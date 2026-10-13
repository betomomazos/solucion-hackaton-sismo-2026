"""
Script para generar la clasificación de riesgo sísmico
basado en los datos de sismicidad de Santander.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def calcular_clasificacion_riesgo(row):
    """
    Clasifica el riesgo sísmico de un evento específico.

    Criterios:
    - Bajo: Magnitud < 3.0 y profundidad > 100km
    - Medio: Magnitud 3.0-4.5 o profundidad 50-100km
    - Alto: Magnitud > 4.5 o profundidad < 50km
    - Crítico: Magnitud > 5.5 y profundidad < 50km
    """
    magnitud = row['magnitud']
    profundidad = row['profundidad']

    if magnitud > 5.5 and profundidad < 50:
        return 'CRÍTICO'
    elif magnitud > 4.5 or profundidad < 50:
        return 'ALTO'
    elif magnitud >= 3.0 or profundidad <= 100:
        return 'MEDIO'
    else:
        return 'BAJO'

def calcular_riesgo_zonal(df):
    """
    Calcula el riesgo promedio por zona (municipio).

    Retorna un DataFrame con estadísticas por zona.
    """
    # Agregar clasificación individual
    df['clasificacion'] = df.apply(calcular_clasificacion_riesgo, axis=1)

    # Estadísticas por zona
    zonas_stats = df.groupby('ubicacion').agg({
        'magnitud': ['mean', 'max', 'std'],
        'profundidad': ['mean', 'min'],
        'clasificacion': lambda x: (x == 'CRÍTICO').sum(),
        'id': 'count'
    }).round(2)

    zonas_stats.columns = ['mag_promedio', 'mag_max', 'mag_std',
                          'prof_promedio', 'prof_min',
                          'eventos_criticos', 'total_eventos']

    # Calcular índice de riesgo (0-100)
    zonas_stats['indice_riesgo'] = (
        (zonas_stats['mag_promedio'] / 7.0) * 40 +
        (zonas_stats['eventos_criticos'] / zonas_stats['total_eventos']) * 30 +
        (1 - zonas_stats['prof_promedio'] / 200) * 30
    ).round(2)

    # Clasificación del riesgo zonal
    zonas_stats['riesgo_zonal'] = pd.cut(
        zonas_stats['indice_riesgo'],
        bins=[0, 30, 50, 70, 100],
        labels=['BAJO', 'MEDIO', 'ALTO', 'CRÍTICO']
    )

    return zonas_stats.reset_index()

def predecir_riesgo_futuro(df, dias=30):
    """
    Predice el riesgo sísmico para los próximos N días
    basado en la frecuencia histórica.
    """
    df['fecha'] = pd.to_datetime(df['fecha'])
    df['mes'] = df['fecha'].dt.month
    df['dia'] = df['fecha'].dt.day

    # Frecuencia mensual
    freq_mensual = df.groupby('mes').size()

    # Promedio mensual ajustado por días
    dias_historicos = (df['fecha'].max() - df['fecha'].min()).days
    eventos_por_dia = len(df) / dias_historicos

    # Predicción para N días
    predicciones = []
    for i in range(dias):
        fecha_futura = datetime.now() + timedelta(days=i)
        mes = fecha_futura.month

        # Factor estacional basado en datos históricos
        factor_estacional = freq_mensual.get(mes, 1) / freq_mensual.mean()

        # Eventos esperados
        eventos_esperados = eventos_por_dia * factor_estacional

        # Magnitud esperada (distribución histórica)
        mag_esperada = df['magnitud'].mean()

        predicciones.append({
            'fecha': fecha_futura.strftime('%Y-%m-%d'),
            'probabilidad_evento': min(eventos_esperados, 1.0),
            'magnitud_esperada': round(mag_esperada, 2),
            'riesgo': 'ALTO' if eventos_esperados > 0.5 else 'MEDIO' if eventos_esperados > 0.2 else 'BAJO'
        })

    return pd.DataFrame(predicciones)

if __name__ == "__main__":
    # Cargar datos
    df = pd.read_csv('data/sismic_data_santander.csv')
    df['fecha'] = pd.to_datetime(df['fecha'])

    # Calcular clasificación
    df['clasificacion'] = df.apply(calcular_clasificacion_riesgo, axis=1)

    # Calcular riesgo zonal
    zonas_stats = calcular_riesgo_zonal(df)

    # Guardar resultados
    df.to_csv('data/sismic_data_clasificado.csv', index=False)
    zonas_stats.to_csv('data/riesgo_zonal.csv', index=False)

    # Predicción futura
    prediccion = predecir_riesgo_futuro(df, dias=30)
    prediccion.to_csv('data/prediccion_riesgo.csv', index=False)

    print("Clasificación completada:")
    print(f"\nDistribución de riesgos:")
    print(df['clasificacion'].value_counts())
    print(f"\nRiesgo por zona:")
    print(zonas_stats[['ubicacion', 'indice_riesgo', 'riesgo_zonal']])
