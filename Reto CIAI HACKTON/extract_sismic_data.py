"""
Script para extraer datos sísmicos del catálogo del Servicio Geológico Colombiano (SGC)
para el departamento de Santander.
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import json

# Configuración
CATALOG_URL = "https://sismo.sgc.gov.co/sismicidad/catalogo"
API_URL = "https://sismo.sgc.gov.co/api/events"

# Coordenadas aproximadas de Santander
SANTANDER_COORDS = {
    "lat_min": 5.5,
    "lat_max": 7.5,
    "lon_min": -74.0,
    "lon_max": -72.5
}

def extract_sismic_data_santander(start_date, end_date, min_magnitude=2.0):
    """
    Extrae datos sísmicos del catálogo SGC para Santander.

    Args:
        start_date (str): Fecha inicial en formato YYYY-MM-DD
        end_date (str): Fecha final en formato YYYY-MM-DD
        min_magnitude (float): Magnitud mínima para filtrar

    Returns:
        DataFrame: Datos sísmicos extraídos
    """
    print(f"Extrayendo datos sísmicos de {start_date} a {end_date}")
    print(f"Región: Santander (Lat: {SANTANDER_COORDS['lat_min']}-{SANTANDER_COORDS['lat_max']}, "
          f"Lon: {SANTANDER_COORDS['lon_min']}-{SANTANDER_COORDS['lon_max']})")

    # Intentar usar la API si está disponible
    try:
        params = {
            "starttime": f"{start_date}T00:00:00",
            "endtime": f"{end_date}T23:59:59",
            "minlatitude": SANTANDER_COORDS["lat_min"],
            "maxlatitude": SANTANDER_COORDS["lat_max"],
            "minlongitude": SANTANDER_COORDS["lon_min"],
            "maxlongitude": SANTANDER_COORDS["lon_max"],
            "minmagnitude": min_magnitude,
            "format": "json",
            "orderby": "time-asc"
        }

        response = requests.get(API_URL, params=params, timeout=30)

        if response.status_code == 200:
            data = response.json()
            if "features" in data:
                events = []
                for feature in data["features"]:
                    props = feature["properties"]
                    coords = feature["geometry"]["coordinates"]
                    events.append({
                        "fecha": props["time"],
                        "magnitud": props["mag"],
                        "profundidad": props.get("depth", None),
                        "ubicacion": props.get("place", ""),
                        "latitud": coords[1],
                        "longitud": coords[0],
                        "tipo": props.get("type", ""),
                        "id": feature["id"]
                    })

                df = pd.DataFrame(events)
                print(f"Se extrajeron {len(df)} eventos sísmicos")
                return df
            else:
                print("No se encontraron eventos en la respuesta")
                return pd.DataFrame()
        else:
            print(f"Error en la API: {response.status_code}")
            return pd.DataFrame()

    except Exception as e:
        print(f"Error al extraer datos: {e}")
        return pd.DataFrame()

def extract_historical_data(years=10):
    """
    Extrae datos históricos de los últimos N años.

    Args:
        years (int): Número de años hacia atrás
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*years)

    return extract_sismic_data_santander(
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d")
    )

if __name__ == "__main__":
    # Extraer datos de los últimos 10 años
    df = extract_historical_data(years=10)

    if not df.empty:
        # Guardar datos
        df.to_csv("data/sismic_data_santander.csv", index=False)
        print(f"Datos guardados en data/sismic_data_santander.csv")
        print(f"\nResumen de datos:")
        print(df.describe())
    else:
        print("No se pudieron extraer datos. Intentando método alternativo...")
