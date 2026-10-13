"""
Script alternativo para extraer datos sísmicos usando web scraping del catálogo SGC.
Este script simula una consulta al catálogo sísmico para Santander.
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import re

def generate_mock_sismic_data():
    """
    Genera datos simulados basados en la sismicidad real de Santander.
    La Mesa de Los Santos es la zona con mayor actividad sísmica recurrente en Colombia.

    Nota: En un entorno de producción, esto debería ser reemplazado por la extracción
    real de datos del catálogo SGC mediante su API o web scraping autorizado.
    """
    print("Generando datos simulados basados en la sismicidad real de Santander...")
    print("Nota: Estos datos son aproximados para el hackathon. Para producción,")
    print("se debe usar la API oficial del SGC o descargar datos del catálogo oficial.")

    # Zonas sísmicas relevantes en Santander
    zonas = {
        "Los Santos": {"lat": 6.81, "lon": -73.15, "frecuencia": 0.6},
        "Bucaramanga": {"lat": 7.13, "lon": -73.12, "frecuencia": 0.15},
        "Piedecuesta": {"lat": 7.00, "lon": -73.05, "frecuencia": 0.10},
        "Girón": {"lat": 7.07, "lon": -73.17, "frecuencia": 0.08},
        "Barichara": {"lat": 6.44, "lon": -73.22, "frecuencia": 0.07}
    }

    events = []
    np.random.seed(42)

    # Generar datos para los últimos 10 años
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*10)

    current_date = start_date
    while current_date <= end_date:
        # Número de eventos por día (Poisson-like)
        daily_events = np.random.poisson(0.5)

        for _ in range(daily_events):
            # Seleccionar zona basado en frecuencia
            zonas_list = list(zonas.keys())
            weights = [zonas[z]["frecuencia"] for z in zonas_list]
            zona = np.random.choice(zonas_list, p=[w/sum(weights) for w in weights])

            # Generar magnitud (distribución Gutenberg-Richter: log(N) = a - b*M)
            # Mayor frecuencia de sismos pequeños
            magnitud = np.random.exponential(1.5) + 2.0
            magnitud = min(magnitud, 7.0)  # Cap en 7.0

            # Profundidad (km) - Santander tiene sismos de profundidad intermedia
            profundidad = np.random.uniform(10, 180)

            # Hora aleatoria del día
            hora = np.random.randint(0, 24)
            minuto = np.random.randint(0, 60)
            segundo = np.random.randint(0, 60)

            fecha_completa = current_date.replace(
                hour=hora, minute=minuto, second=segundo
            )

            # Pequeña variación en coordenadas
            lat_var = np.random.uniform(-0.1, 0.1)
            lon_var = np.random.uniform(-0.1, 0.1)

            events.append({
                "fecha": fecha_completa.strftime("%Y-%m-%d %H:%M:%S"),
                "magnitud": round(magnitud, 2),
                "profundidad": round(profundidad, 2),
                "ubicacion": zona,
                "latitud": round(zonas[zona]["lat"] + lat_var, 4),
                "longitud": round(zonas[zona]["lon"] + lon_var, 4),
                "tipo": "terremoto",
                "id": f"SGC-{len(events) + 1}"
            })

        current_date += timedelta(days=1)

    df = pd.DataFrame(events)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df.sort_values("fecha").reset_index(drop=True)

    print(f"Se generaron {len(df)} eventos sísmicos simulados")
    return df

if __name__ == "__main__":
    import numpy as np

    # Generar datos
    df = generate_mock_sismic_data()

    # Crear directorio data si no existe
    import os
    os.makedirs("data", exist_ok=True)

    # Guardar datos
    df.to_csv("data/sismic_data_santander.csv", index=False)
    print(f"Datos guardados en data/sismic_data_santander.csv")
    print(f"\nResumen de datos:")
    print(df.describe())
    print(f"\nDistribución por ubicación:")
    print(df["ubicacion"].value_counts())
