# Comandos para ejecutar el proyecto

## Instalación (primer vez en un PC nuevo)

### Opción 1: Automática (recomendada)

**Windows:**
```bash
INSTALL.bat
```

**Linux/Mac:**
```bash
chmod +x INSTALL.sh
./INSTALL.sh
```

### Opción 2: Manual

1. Instalar dependencias:
```bash
pip install -r requirements.txt
```

2. Generar datos sismicos (si no existen):
```bash
python extract_sismic_data_alternative.py
python generar_clasificacion.py
```

3. Agregar variables derivadas (opcional, para visualizaciones avanzadas):
```bash
python agregar_variables_derivadas.py
```

## Para encender el proyecto

### Iniciar la aplicación web Flask
```bash
python app.py
```

La aplicación estará disponible en: http://localhost:5000

### Otras opciones de dashboard

**Dashboard Streamlit:**
```bash
streamlit run dashboard_simple.py
```

**Dashboard Avanzado:**
```bash
streamlit run dashboard_avanzado.py
```

## Archivos necesarios para copiar a otro PC

Para copiar el proyecto a otro PC, necesitas copiar toda la carpeta excepto:
- `venv/` (si existe, se crea automáticamente en el nuevo PC)
- `__pycache__/` (se crea automáticamente)
- `.git/` (si usas git)

**Archivos obligatorios:**
- `app.py` - Backend Flask
- `requirements.txt` - Dependencias
- `templates/` - Carpeta con archivos HTML
- `info_registros/` - Carpeta con datos (CSV)
- `static/` - Archivos estáticos (si existe)

**Archivos opcionales (scripts y visualizaciones):**
- `graficos_sismos.py` - Funciones de visualización
- `agregar_variables_derivadas.py` - Script para agregar variables
- `dashboard_simple.py` - Dashboard Streamlit básico
- `dashboard_avanzado.py` - Dashboard Streamlit avanzado
- `extract_sismic_data_alternative.py` - Generador de datos
- `generar_clasificacion.py` - Clasificador de riesgo

## Solución de problemas

### Error: "No module named 'pandas'"
```bash
pip install -r requirements.txt
```

### Error: "Python no está instalado"
Descarga e instala Python 3.11+ desde: https://www.python.org/downloads/

### Error: Puerto 5000 ya está en uso
Cambia el puerto en `app.py` (línea final):
```python
app.run(debug=True, port=5001)  # Cambiar a otro puerto
```

### Usar entorno virtual (recomendado para desarrollo)

**Crear entorno virtual:**
```bash
python -m venv venv
```

**Activar entorno virtual:**
- Windows: `venv\Scripts\activate`
- Linux/Mac: `source venv/bin/activate`

**Instalar dependencias en el entorno:**
```bash
pip install -r requirements.txt
```

**Ejecutar aplicación:**
```bash
python app.py
```
