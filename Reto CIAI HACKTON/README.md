# Sistema de Clasificacion de Riesgo Sismico - Santander

## IA, informes y funcionamiento sin internet

La aplicación Flask incluye **IA e informes** con presentación formal y exportación
a PDF. Permite analizar el rack local,
cargar un CSV desde la página, consultar el catálogo oficial USGS de los últimos
90 días, contrastar registros y descargar un informe JSON con fuentes, calidad,
validación y conclusión. El PDF incluye resumen ejecutivo, tablas y gráfico
territorial, escenarios, evaluación temporal y referencias. No requiere claves
de API ni un servicio de IA remoto.

Inicio de la aplicación y sus dependencias mínimas (Python 3.10 o superior):

```powershell
python -m pip install -r requirements-ia.txt
python app.py
```

Abra `http://localhost:5000`, seleccione **IA e informes** y pulse **Analizar y
generar informe**. Las dependencias deben estar instaladas antes de trabajar sin
conexión. El servidor local debe permanecer en ejecución.

- El rack canónico es `info_registros/dataset_sismos_bucaramanga.csv`.
  Los archivos derivados contienen variables inferidas y no se mezclan con él.
- El CSV opcional acepta `fecha`, `magnitud`, `latitud`, `longitud`, con `ubicacion`
  e `id` opcionales, o los nombres originales SGC. Tamaño máximo de solicitud:
  5 MB. ISO 8601 sin zona se interpreta en UTC; el formato SGC `DD/AAAA/MM HH:MM:SS`
  se interpreta en hora colombiana y se convierte a UTC.
- Se informan filas inválidas, duplicadas y fuera de zona. La ventana de estudio
  es latitud 5.4 a 8.4 y longitud -74.7 a -72.0; no equivale al límite
  administrativo de Santander. Un reporte de Bucaramanga puede tener epicentro
  en otro país y se excluye si queda fuera de esa ventana.
- El contraste usa un intervalo común y la misma magnitud mínima. Empareja
  eventos uno a uno con tolerancias de 60 segundos, 20 km y 0.3 de magnitud.
  Diferencias entre catálogos no demuestran que un registro sea falso. Se mantienen
  estimaciones independientes para evitar mezclar coberturas instrumentales
  con reportes de percepción.
- La consulta HTTPS tiene tiempos de espera limitados. El último resultado válido
  se guarda mediante reemplazo atómico en `data/usgs_cache.json`. Sin internet o
  si USGS falla, se usa el rack y esa copia, indicando su fecha. Si no existe una
  copia válida, el informe usa sólo el rack. Desmarcar la consulta web evita toda
  solicitud remota del analizador. Los mapas y gráficos que dependen de CDN pueden
  no estar disponibles sin internet; las tablas e informes usan recursos locales.

### Modelo refinado y explicación territorial

Random Forest y regresión logística compiten para estimar la probabilidad de al
menos un **registro** diario por encima de la magnitud elegida. Usan siete
variables: registros del día anterior y de hace siete días, frecuencias de 7,
30 y 90 días y diferencias entre esas frecuencias. Se usan hasta diez años de
historia y sólo días completos. Requiere al menos 365 días y 20 ejemplos de cada clase para evaluarse;
la referencia Poisson requiere al menos 60 días de historial.

La selección compara ambos candidatos en tres ventanas temporales expansivas
dentro del primer 80% del historial. El candidato con menor Brier medio se evalúa
una sola vez en el 20% final, posterior a esas ventanas. Las variables sólo usan
registros anteriores al objetivo. Se informa Brier (menor es mejor), resultados
de cada ventana y frecuencia observada frente a probabilidades medias en la
prueba final. Sólo se usa el candidato si supera Poisson tanto en el promedio
de validación como en la prueba final;
en caso contrario se utiliza la frecuencia histórica Poisson. Con catálogos de
más de siete días de antigüedad también se usa la referencia y se advierte que
no describe actividad actual. Para días futuros sucesivos se reutilizan
probabilidades como entradas; ese horizonte múltiple no está validado.

El informe explica las diez zonas con más registros, su participación en el
catálogo, magnitudes observadas y conteos de los últimos 30 días frente a los
30 días anteriores. Si el CSV no aporta ubicación, agrupa por celdas aproximadas
de 0.25 grados, sin asignar nombres municipales. Las probabilidades por zona usan
un periodo común de exposición y una referencia Poisson; no son modelos
municipales validados. Se omiten con menos de 60 días de exposición.

Los escenarios distinguen ningún registro, un registro y dos o más registros
sobre el umbral durante el horizonte elegido. Se informa la categoría más
probable, el conteo esperado y modal, un intervalo predictivo de conteos con tasa
puntual y un intervalo exacto Poisson del 95% para la probabilidad de al menos un
registro. Son escenarios de referencia con tasa constante e independencia;
no modelan réplicas, subregistro, daños ni incertidumbre de cobertura. Los pesos
de variables, cuando se usa un clasificador, expresan asociación y no causalidad.

**Esto no predice la fecha, el epicentro ni la magnitud de un sismo individual,
ni es un sistema de alerta temprana.** La ausencia de reportes no demuestra la
ausencia de sismos y el catálogo de percepción no es completo. No utilizar para
decidir evacuaciones. Consulte los [límites científicos descritos por USGS](https://www.usgs.gov/faqs/can-you-predict-earthquakes)
y la [documentación del catálogo USGS](https://earthquake.usgs.gov/fdsnws/event/1/).
Las profundidades estimadas de las pantallas anteriores son aproximaciones
heredadas; el modelo nuevo no las usa.

### API nueva y cambio de predicción

`GET /api/analisis?web=false&magnitud_minima=3.5&dias=7` genera un informe sin
consulta remota. `POST /api/analisis` acepta formulario multipart con `archivo`
(CSV opcional), `web` (`true` o `false`), `magnitud_minima` (-2 a 10) y `dias`
(1 a 30). Retorna `modo`, `fuentes`, `resumen`, `contraste`, `prediccion`,
`prediccion_web`, `advertencias`, `conclusion` y `referencias`.

También retorna `analisis_territorial` y `export_token`. **Exportar informe PDF**
envía el token a `POST /api/informes/pdf`, con JSON `{"token": "..."}`. El servidor
verifica la firma y genera el PDF del mismo informe mostrado, sin nuevas consultas
ni reentrenamiento. La exportación funciona sin internet y las respuestas PDF no
se almacenan en caché. El token vence después de 24 horas; al reiniciar el servidor
también vence si no se configura una `FLASK_SECRET_KEY` estable. En varios procesos
de servidor debe compartirse esa clave. No se requiere configurarla para uso local.

`GET /api/prediccion` ahora devuelve un objeto con `disponible`, `dias`,
metodología y validación; reemplaza la antigua lista con magnitudes aleatorias.
Si no hay historial suficiente, `dias` queda vacío y se explica el motivo.

Pruebas automatizadas:

```powershell
python -m pip install -r requirements-test.txt
python -m unittest test_analisis_sismico -v
```

Proyecto desarrollado para el Hackathon CIAI 2026. Sistema de analisis y clasificacion de riesgo sismico para zonas de Santander, Colombia, utilizando datos del Servicio Geologico Colombiano (SGC).

## Arquitectura

Este proyecto utiliza una arquitectura web moderna con:

- **Backend**: Flask (Python) - API REST para procesamiento de datos y clasificacion
- **Frontend**: JavaScript (Vanilla) + HTML + CSS - Interfaz web interactiva
- **Visualizaciones**: Chart.js (graficos) y Leaflet (mapas interactivos)

## Contenido

Este proyecto incluye visualizaciones y demostraciones para los 3 niveles del hackathon:

### Nivel Basico
- **Demostracion**: Interfaz web con entrada y resultado de clasificacion en tiempo real
- Endpoint: `/api/clasificar` - API para clasificar eventos sismicos
- Funcionalidad: Ingrese magnitud, profundidad y ubicacion para obtener clasificacion

### Nivel Medio
- **Prototipo y Visualizacion Territorial**: Mapa interactivo comparando unidades territoriales
- Endpoint: `/api/zonas` - API para datos de todas las zonas
- Visualizaciones:
  - Mapa interactivo con circulos de riesgo por municipio (Leaflet)
  - Graficos comparativos por zona (Chart.js)
  - Tabla comparativa detallada

### Nivel Avanzado
- **Flujo Funcional y Verificable**: Dashboard completo con priorizacion y analisis
- Endpoints:
  - `/api/dashboard` - Metricas generales
  - `/api/priorizacion` - Sistema de priorizacion
  - `/api/prediccion` - Prediccion de riesgo
  - `/api/estadisticas` - Estadisticas detalladas
- Funcionalidades:
  - Dashboard principal con metricas
  - Clasificacion en tiempo real
  - Sistema de priorizacion de zonas
  - Analisis detallado con predicciones

## Instalacion Rapida

### Windows
Ejecutar el script de instalacion automatica:
```bash
INSTALL.bat
```

### Linux/Mac
Ejecutar el script de instalacion automatica:
```bash
chmod +x INSTALL.sh
./INSTALL.sh
```

### Instalacion Manual

1. Clonar o descargar el repositorio

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Generar datos sismicos (si no existen):
```bash
python extract_sismic_data_alternative.py
python generar_clasificacion.py
```

4. Agregar variables derivadas al dataset (opcional, para visualizaciones avanzadas):
```bash
python agregar_variables_derivadas.py
```

## Uso

### Iniciar la aplicacion web

Ejecutar el servidor Flask:
```bash
python app.py
```

La aplicacion estara disponible en: http://localhost:5000

### Navegacion

La aplicacion web tiene 5 secciones:

1. **Dashboard**: Metricas generales y graficos de distribucion de riesgo
2. **Clasificacion**: Ingrese datos de un sismo para clasificarlo en tiempo real
3. **Mapa**: Mapa interactivo de riesgo por municipio
4. **Priorizacion**: Sistema de ranking de prioridad de atencion por zona
5. **Analisis**: Predicciones a 7 dias y estadisticas detalladas

## API Endpoints

### GET `/api/dashboard`
Retorna metricas generales del sistema.

**Respuesta:**
```json
{
  "metricas": {
    "total_eventos": 1834,
    "zonas_monitoreadas": 5,
    "eventos_criticos": 41,
    "max_indice_riesgo": 36.83
  },
  "distribucion_riesgo": {
    "BAJO": 432,
    "MEDIO": 752,
    "ALTO": 609,
    "CRITICO": 41
  }
}
```

### POST `/api/clasificar`
Clasifica un evento sismico.

**Body:**
```json
{
  "magnitud": 4.2,
  "profundidad": 35,
  "ubicacion": "Los Santos"
}
```

**Respuesta:**
```json
{
  "riesgo": "ALTO",
  "magnitud": 4.2,
  "profundidad": 35,
  "ubicacion": "Los Santos",
  "eventos_similares": [...],
  "total_similares": 15
}
```

### GET `/api/zonas`
Retorna datos de todas las zonas con indice de riesgo.

### GET `/api/priorizacion`
Retorna ranking de prioridad de atencion por zona.

### GET `/api/prediccion`
Retorna prediccion de riesgo a 7 dias.

### GET `/api/estadisticas`
Retorna estadisticas detalladas por zona.

### GET `/api/eventos`
Retorna eventos sismicos (parametro opcional: limit).

## Estructura del Proyecto

```
Reto CIAI HACKTON/
├── data/                           # Datos generados
│   ├── sismic_data_santander.csv          # Datos sismicos brutos
│   ├── sismic_data_clasificado.csv        # Datos con clasificacion
│   ├── riesgo_zonal.csv                   # Riesgo por zona
│   └── prediccion_riesgo.csv              # Prediccion a 30 dias
├── templates/                      # Plantillas HTML
│   └── index.html                          # Interfaz web principal
├── static/                         # Archivos estaticos (opcional)
├── app.py                          # Backend Flask - API REST
├── demo_basica.ipynb              # Notebook nivel basico (opcional)
├── visualizacion_territorial.py   # Script nivel medio (opcional)
├── dashboard_simple.py             # Dashboard Streamlit (opcional)
├── extract_sismic_data_alternative.py      # Generacion de datos
├── generar_clasificacion.py                # Clasificacion de riesgo
├── requirements.txt                       # Dependencias
└── README.md                              # Este archivo
```

## Metodologia de Clasificacion

El sistema clasifica el riesgo sismico en 4 niveles:

- **CRITICO**: Magnitud > 5.5 y profundidad < 50km
- **ALTO**: Magnitud > 4.5 o profundidad < 50km
- **MEDIO**: Magnitud >= 3.0 o profundidad <= 100km
- **BAJO**: Cualquier otro caso

### Indice de Riesgo Zonal (0-100)

Calculado combinando:
- Magnitud promedio (40%)
- Proporcion de eventos criticos (30%)
- Profundidad promedio (30%)

### Sistema de Priorizacion

El score de prioridad considera:
- Indice de riesgo (40%)
- Frecuencia de eventos criticos (30%)
- Magnitud maxima historica (20%)
- Profundidad minima (10%)

## Datos

Los datos utilizados son registros sismicos reales del Servicio Geologico Colombiano (SGC), proporcionados en el archivo `info_registros/dataset_sismos_bucaramanga.csv`.

**Caracteristicas del dataset:**
- 862 eventos sismicos registrados
- Periodo: 2025-2026
- Zona: Departamento de Santander, Colombia
- Reportado desde: Bucaramanga

**Zonas analizadas:**
- Los Santos (zona con mayor actividad sismica recurrente)
- Zapatoca
- Villanueva
- Simacota
- Surata
- El Playon
- Galan
- Velez
- Rionegro
- Cachira
- Y otras zonas de Santander

**Fuente de datos:** Servicio Geologico Colombiano (SGC)

## Dependencias

- pandas==2.1.4
- numpy==1.26.3
- requests==2.31.0
- matplotlib==3.8.2
- seaborn==0.13.1
- scikit-learn==1.4.0
- folium==0.15.1
- streamlit==1.31.0
- python-dotenv==1.0.0
- tqdm==4.66.1
- flask==3.0.0
- flask-cors==4.0.0

## Tecnologias Frontend

- HTML5
- CSS3
- JavaScript (Vanilla)
- Chart.js (graficos)
- Leaflet (mapas)

## Equipo

Este proyecto fue desarrollado para el Hackathon CIAI 2026.

## Licencia

Los datos sismicos son propiedad del Servicio Geologico Colombiano (SGC). El codigo de este proyecto es de uso educativo para el hackathon.

## Agradecimientos

- Servicio Geologico Colombiano (SGC) por los datos sismicos
- Organizadores del Hackathon CIAI 2026

---

**Ultima actualizacion:** Octubre 2026
