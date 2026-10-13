"""
Backend Flask - API para el Sistema de Clasificacion de Riesgo Sismico
Proporciona endpoints para clasificacion, datos y analisis.
"""

from flask import Flask, jsonify, request, render_template, send_file
from flask_cors import CORS
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from analisis_sismico import BOUNDS, build_report, forecast, normalize, read_csv, LOCAL
from informe_pdf import render_report
from io import BytesIO
import os
import secrets
from itsdangerous import URLSafeTimedSerializer, BadSignature

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY') or secrets.token_hex(32)


def report_signer():
    return URLSafeTimedSerializer(app.config['SECRET_KEY'], salt='informe-sismico-v1')

# Colores por nivel de riesgo
COLORS = {
    'BAJO': '#2ecc71',
    'MEDIO': '#f1c40f',
    'ALTO': '#e67e22',
    'CRITICO': '#e74c3c'
}

def cargar_datos():
    """Carga los datos sismicos reales del dataset."""
    df = read_csv(LOCAL.read_bytes())

    # Parsear fecha manualmente debido al formato no estandar
    def parse_fecha(fecha_str):
        try:
            parts = fecha_str.split(' ')
            date_part = parts[0]
            time_part = parts[1] if len(parts) > 1 else '00:00:00'

            # Formato esperado: DD/AAAA/MM HH:MM:SS
            date_parts = date_part.split('/')
            if len(date_parts) == 3:
                day = int(date_parts[0])
                year = int(date_parts[1])
                month = int(date_parts[2])
                return f"{year:04d}-{month:02d}-{day:02d} {time_part}"
        except:
            pass
        return None

    df['fecha'] = df['Fecha_Hora_Completa'].apply(parse_fecha)
    df = df[df['fecha'].notna()].copy()
    df['fecha'] = pd.to_datetime(df['fecha'])

    # Renombrar columnas para consistencia
    df = df.rename(columns={
        'Magnitud': 'magnitud',
        'Latitud': 'latitud',
        'Longitud': 'longitud',
        'Municipio_Epicentral': 'ubicacion',
        'Intensidad_Maxima': 'intensidad'
    })

    # Filtrar solo eventos en Santander
    df = df[df['Departamento_Reporte'] == 'SANTANDER'].copy()
    df = df[df.latitud.between(BOUNDS['minlatitude'], BOUNDS['maxlatitude']) &
            df.longitud.between(BOUNDS['minlongitude'], BOUNDS['maxlongitude'])].copy()

    # Calcular profundidad estimada basada en intensidad (aproximacion)
    df['profundidad_estimada'] = True
    df['profundidad'] = df['intensidad'] * 30  # Aproximacion: intensidad * 30km

    # Calcular clasificacion de riesgo
    df['clasificacion'] = df.apply(lambda row: clasificar_riesgo(row['magnitud'], row['profundidad']), axis=1)

    # Agregación con nombres explícitos para evitar cruzar conteos y coordenadas.
    riesgo_zonal = df.groupby('ubicacion').agg(
        mag_promedio=('magnitud', 'mean'), mag_max=('magnitud', 'max'),
        mag_std=('magnitud', 'std'), total_eventos=('magnitud', 'count'),
        prof_promedio=('profundidad', 'mean'), prof_min=('profundidad', 'min'),
        latitud=('latitud', 'mean'), longitud=('longitud', 'mean'),
        eventos_criticos=('clasificacion', lambda x: (x == 'CRITICO').sum())
    ).round(2).reset_index()
    riesgo_zonal['mag_std'] = riesgo_zonal['mag_std'].fillna(0)
    riesgo_zonal = riesgo_zonal[riesgo_zonal['total_eventos'] >= 5].copy()

    # Calcular indice de riesgo simplificado
    max_eventos = riesgo_zonal['total_eventos'].max() if len(riesgo_zonal) > 0 else 1
    riesgo_zonal['indice_riesgo'] = (
        (riesgo_zonal['mag_promedio'] / 7.0) * 50 +
        (riesgo_zonal['total_eventos'] / max_eventos) * 50
    ).round(2)

    # Asegurar que el indice este entre 0 y 100
    riesgo_zonal['indice_riesgo'] = riesgo_zonal['indice_riesgo'].clip(0, 100)

    # Clasificacion del riesgo zonal
    riesgo_zonal['riesgo_zonal'] = pd.cut(
        riesgo_zonal['indice_riesgo'],
        bins=[0, 30, 50, 70, 100],
        labels=['BAJO', 'MEDIO', 'ALTO', 'CRITICO']
    )

    prediccion = pd.DataFrame()

    return df, riesgo_zonal, prediccion

def clasificar_riesgo(magnitud, profundidad):
    """Clasifica el riesgo sismico."""
    if magnitud > 5.5 and profundidad < 50:
        return 'CRITICO'
    elif magnitud > 4.5 or profundidad < 50:
        return 'ALTO'
    elif magnitud >= 3.0 or profundidad <= 100:
        return 'MEDIO'
    else:
        return 'BAJO'

def calcular_prioridad_zona(riesgo_zonal):
    """Calcula la prioridad de atencion por zona."""
    prioridad = riesgo_zonal.copy()
    prioridad['score_prioridad'] = (
        (prioridad['indice_riesgo'] / 100) * 40 +
        (prioridad['eventos_criticos'] / prioridad['total_eventos']) * 30 +
        (prioridad['mag_max'] / 7.0) * 20 +
        (1 - prioridad['prof_min'] / 200) * 10
    )
    prioridad['nivel_prioridad'] = pd.cut(
        prioridad['score_prioridad'],
        bins=[0, 30, 50, 70, 100],
        labels=['BAJA', 'MEDIA', 'ALTA', 'CRITICA']
    )
    prioridad = prioridad.sort_values('score_prioridad', ascending=False)
    return prioridad

@app.route('/')
def index():
    """Pagina principal."""
    return render_template('index.html')

@app.route('/api/dashboard')
def get_dashboard():
    """Endpoint para datos del dashboard."""
    df, riesgo_zonal, prediccion = cargar_datos()

    metricas = {
        'total_eventos': int(len(df)),
        'zonas_monitoreadas': int(len(riesgo_zonal)),
        'eventos_criticos': int(len(df[df['clasificacion'] == 'CRITICO'])),
        'max_indice_riesgo': float(riesgo_zonal['indice_riesgo'].max()) if len(riesgo_zonal) > 0 and not pd.isna(riesgo_zonal['indice_riesgo'].max()) else 0.0
    }

    distribucion_riesgo = df['clasificacion'].value_counts().to_dict()

    return jsonify({
        'metricas': metricas,
        'distribucion_riesgo': distribucion_riesgo
    })

@app.route('/api/clasificar', methods=['POST'])
def clasificar():
    """Endpoint para clasificar un evento sismico."""
    data = request.json
    magnitud = float(data.get('magnitud', 0))
    profundidad = float(data.get('profundidad', 0))
    ubicacion = data.get('ubicacion', 'Desconocido')

    riesgo = clasificar_riesgo(magnitud, profundidad)

    # Buscar eventos similares
    df, _, _ = cargar_datos()

    # Buscar por magnitud y ubicacion similar
    similares = df[
        (df['magnitud'].between(magnitud - 1.0, magnitud + 1.0)) &
        (df['ubicacion'] == ubicacion)
    ].head(10)

    # Si no hay suficientes, buscar solo por magnitud
    if len(similares) < 5:
        similares = df[
            df['magnitud'].between(magnitud - 1.0, magnitud + 1.0)
        ].head(10)

    similares_json = similares[['fecha', 'magnitud', 'profundidad',
                                 'ubicacion', 'clasificacion']].to_dict('records')

    return jsonify({
        'riesgo': riesgo,
        'magnitud': magnitud,
        'profundidad': profundidad,
        'ubicacion': ubicacion,
        'eventos_similares': similares_json,
        'total_similares': len(similares)
    })

@app.route('/api/zonas')
def get_zonas():
    """Endpoint para datos de todas las zonas."""
    _, riesgo_zonal, _ = cargar_datos()

    zonas = riesgo_zonal.to_dict('records')
    for zona in zonas:
        zona['color'] = COLORS.get(zona['riesgo_zonal'], '#95a5a6')
        # Asegurar que latitud y longitud sean float
        zona['latitud'] = float(zona['latitud']) if pd.notna(zona['latitud']) else 0
        zona['longitud'] = float(zona['longitud']) if pd.notna(zona['longitud']) else 0

    return jsonify(zonas)

@app.route('/api/priorizacion')
def get_priorizacion():
    """Endpoint para sistema de priorizacion."""
    _, riesgo_zonal, _ = cargar_datos()
    prioridad = calcular_prioridad_zona(riesgo_zonal)

    prioridad_json = prioridad.to_dict('records')
    for zona in prioridad_json:
        zona['color'] = COLORS.get(zona['riesgo_zonal'], '#95a5a6')

    return jsonify(prioridad_json)

@app.route('/api/prediccion')
def get_prediccion():
    """Endpoint para prediccion de riesgo."""
    normalized, _ = normalize(read_csv(LOCAL.read_bytes()), 'Rack local SGC')
    return jsonify(forecast(normalized))

@app.route('/api/estadisticas')
def get_estadisticas():
    """Endpoint para estadisticas detalladas."""
    df, _, _ = cargar_datos()

    # Filtrar solo zonas con suficientes eventos
    zona_counts = df['ubicacion'].value_counts()
    zonas_validas = zona_counts[zona_counts >= 5].index
    df_filtrado = df[df['ubicacion'].isin(zonas_validas)].copy()

    stats = df_filtrado.groupby('ubicacion').agg({
        'magnitud': ['mean', 'max', 'std'],
        'profundidad': 'mean',
        'clasificacion': lambda x: (x == 'CRITICO').sum(),
        'latitud': 'mean',
        'longitud': 'mean'
    }).round(2)

    stats.columns = ['mag_promedio', 'mag_maxima', 'desv_mag',
                     'prof_promedio', 'eventos_criticos',
                     'latitud', 'longitud']
    stats_json = stats.reset_index().to_dict('records')

    return jsonify(stats_json)

@app.route('/api/eventos')
def get_eventos():
    """Endpoint para obtener eventos sismicos."""
    df, _, _ = cargar_datos()

    limit = request.args.get('limit', 100, type=int)
    eventos = df.head(limit).to_dict('records')

    # Asegurar que las coordenadas sean float
    for evento in eventos:
        evento['latitud'] = float(evento['latitud']) if pd.notna(evento['latitud']) else 0
        evento['longitud'] = float(evento['longitud']) if pd.notna(evento['longitud']) else 0
        evento['magnitud'] = float(evento['magnitud']) if pd.notna(evento['magnitud']) else 0

    return jsonify(eventos)

@app.route('/api/analisis', methods=['GET', 'POST'])
def analizar_catalogos():
    """Informe local/web y CSV opcional, sin credenciales ni servicios de IA remotos."""
    try:
        options = request.form if request.method == 'POST' else request.args
        threshold = float(options.get('magnitud_minima', 3.5))
        days = int(options.get('dias', 7))
        if not np.isfinite(threshold) or not -2 <= threshold <= 10 or not 1 <= days <= 30:
            raise ValueError('Magnitud entre -2 y 10; horizonte entre 1 y 30 días.')
        online = options.get('web', 'true').lower() not in ('false', '0', 'no')
        upload = request.files.get('archivo')
        raw = upload.read() if upload and upload.filename else None
        if raw is not None and not raw:
            raise ValueError('El archivo CSV está vacío.')
        report = build_report(raw, online, threshold, days)
        # Exportar exactamente el informe mostrado, sin repetir la consulta ni confiar en su edición en el navegador.
        return jsonify(dict(report, export_token=report_signer().dumps(report)))
    except (ValueError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        return jsonify(error=str(exc)), 400
    except OSError:
        return jsonify(error='No se pudo leer el rack local. Compruebe info_registros y sus permisos.'), 503


@app.route('/api/informes/pdf', methods=['POST'])
def exportar_pdf():
    payload = request.get_json(silent=True)
    token = payload.get('token') if isinstance(payload, dict) else None
    if not isinstance(token, str) or not token:
        return jsonify(error='Genere un informe antes de exportar el PDF.'), 400
    try:
        report = report_signer().loads(token, max_age=86400)
    except BadSignature:
        return jsonify(error='El informe venció o su firma no es válida. Genere el informe nuevamente.'), 400
    pdf = render_report(report)
    response = send_file(BytesIO(pdf), mimetype='application/pdf', as_attachment=True,
                         download_name='informe-sismico.pdf', max_age=0)
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.errorhandler(413)
def archivo_grande(error):
    return jsonify(error='El tamaño máximo de la solicitud es 5 MB.'), 413


if __name__ == '__main__':
    print("Iniciando servidor Flask en http://localhost:5000")
    app.run(debug=True, port=5000)
