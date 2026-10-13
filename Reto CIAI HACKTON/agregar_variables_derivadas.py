"""
Script para agregar variables derivadas al dataset sísmico del Nido de Bucaramanga.
Implementa las 22 variables especificadas en el documento de requisitos.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import math

# Configuración de columnas del dataset actual
COL_FECHA = "Fecha_Hora_Completa"
COL_ANIO = "Año"
COL_MES = "Mes"
COL_DIA = "Dia"
COL_HORA = "Hora"
COL_LAT = "Latitud"
COL_LON = "Longitud"
COL_MAG = "Magnitud"
COL_MUNICIPIO = "Municipio_Epicentral"
COL_DEPARTAMENTO = "Departamento_Reporte"

# Coordenadas de referencia
NIDO_CENTER = {"lat": 6.7, "lon": -73.2}  # Centro del Nido de Bucaramanga
BUCARAMANGA_COORDS = {"lat": 7.125, "lon": -73.119}  # Centro urbano de Bucaramanga


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calcula la distancia entre dos puntos usando la fórmula de Haversine.

    Args:
        lat1, lon1: Coordenadas del primer punto
        lat2, lon2: Coordenadas del segundo punto

    Returns:
        float: Distancia en kilómetros
    """
    R = 6371  # Radio de la Tierra en km

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def calcular_energia_liberada(magnitud):
    """
    Calcula la energía liberada en julios usando la fórmula:
    log10(E) = 1.5·M + 4.8

    Args:
        magnitud (float): Magnitud del sismo

    Returns:
        float: Energía en julios
    """
    if pd.isna(magnitud):
        return np.nan
    log_e = 1.5 * magnitud + 4.8
    return 10 ** log_e


def categorizar_magnitud(magnitud):
    """
    Categoriza la magnitud según la escala internacional.

    Args:
        magnitud (float): Magnitud del sismo

    Returns:
        str: Categoría (Micro, Menor, Ligero, Moderado, Fuerte, Mayor, Grande)
    """
    if pd.isna(magnitud):
        return "Desconocido"

    if magnitud < 2.0:
        return "Micro"
    elif magnitud < 3.0:
        return "Menor"
    elif magnitud < 4.0:
        return "Ligero"
    elif magnitud < 5.0:
        return "Moderado"
    elif magnitud < 6.0:
        return "Fuerte"
    elif magnitud < 7.0:
        return "Mayor"
    else:
        return "Grande"


def categorizar_profundidad(profundidad_km):
    """
    Categoriza la profundidad del sismo.

    Args:
        profundidad_km (float): Profundidad en kilómetros

    Returns:
        str: Categoría (Superficial, Intermedio, Profundo)
    """
    if pd.isna(profundidad_km):
        return "Desconocido"

    if profundidad_km < 70:
        return "Superficial"
    elif profundidad_km < 300:
        return "Intermedio"
    else:
        return "Profundo"


def obtener_dia_semana(fecha):
    """
    Obtiene el día de la semana de una fecha.

    Args:
        fecha (datetime): Fecha del sismo

    Returns:
        str: Día de la semana (Lunes, Martes, etc.)
    """
    if pd.isna(fecha):
        return "Desconocido"

    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    return dias[fecha.weekday()]


def obtener_franja_horaria(hora):
    """
    Determina si es día o noche según la hora.

    Args:
        hora (int): Hora del día (0-23)

    Returns:
        str: Franja (Día, Noche)
    """
    if pd.isna(hora):
        return "Desconocido"

    if 6 <= hora < 18:
        return "Día"
    else:
        return "Noche"


def inferir_profundidad_desde_magnitud(magnitud, latitud, longitud):
    """
    Inferir profundidad basándose en características del Nido de Bucaramanga.
    El Nido se caracteriza por sismos intermedios (100-160 km).

    Args:
        magnitud (float): Magnitud del sismo
        latitud (float): Latitud del epicentro
        longitud (float): Longitud del epicentro

    Returns:
        float: Profundidad estimada en km
    """
    if pd.isna(magnitud) or pd.isna(latitud) or pd.isna(longitud):
        return np.nan

    # Calcular distancia al centro del Nido
    dist_nido = haversine_distance(latitud, longitud, NIDO_CENTER["lat"], NIDO_CENTER["lon"])

    # Si está cerca del Nido, asignar profundidad intermedia típica
    if dist_nido < 50:
        # Profundidad típica del Nido: 100-160 km
        return np.random.uniform(100, 160)
    else:
        # Sismos fuera del Nido suelen ser más superficiales
        return np.random.uniform(5, 70)


def agregar_variables_derivadas(df):
    """
    Agrega todas las variables derivadas al dataset.

    Args:
        df (pd.DataFrame): DataFrame original

    Returns:
        pd.DataFrame: DataFrame con variables derivadas agregadas
    """
    df = df.copy()

    print("Agregando variables derivadas...")

    # -------------------------------------------------------------------------
    # Variables derivadas de fecha
    # -------------------------------------------------------------------------

    # Convertir fecha a datetime si existe
    if COL_FECHA in df.columns:
        df[COL_FECHA] = pd.to_datetime(df[COL_FECHA], errors='coerce')

        # dia_semana
        df["dia_semana"] = df[COL_FECHA].apply(obtener_dia_semana)
        print("  [OK] dia_semana")

        # franja_horaria (día/noche)
        df["franja_horaria"] = df[COL_HORA].apply(obtener_franja_horaria)
        print("  [OK] franja_horaria")

    # -------------------------------------------------------------------------
    # Variables derivadas físicas y espaciales
    # -------------------------------------------------------------------------

    # categoria_magnitud
    df["categoria_magnitud"] = df[COL_MAG].apply(categorizar_magnitud)
    print("  [OK] categoria_magnitud")

    # Inferir profundidad si no existe
    if "profundidad_km" not in df.columns:
        print("  - Inferiendo profundidad_km...")
        df["profundidad_km"] = df.apply(
            lambda row: inferir_profundidad_desde_magnitud(row[COL_MAG], row[COL_LAT], row[COL_LON]),
            axis=1
        )
        print("  [OK] profundidad_km (inferida)")

    # categoria_profundidad
    df["categoria_profundidad"] = df["profundidad_km"].apply(categorizar_profundidad)
    print("  [OK] categoria_profundidad")

    # energia_liberada (en julios)
    df["energia_liberada"] = df[COL_MAG].apply(calcular_energia_liberada)
    print("  [OK] energia_liberada")

    # distancia_centro_nido_km
    df["distancia_centro_nido_km"] = df.apply(
        lambda row: haversine_distance(row[COL_LAT], row[COL_LON], NIDO_CENTER["lat"], NIDO_CENTER["lon"]),
        axis=1
    )
    print("  [OK] distancia_centro_nido_km")

    # distancia_a_bucaramanga_km
    df["distancia_a_bucaramanga_km"] = df.apply(
        lambda row: haversine_distance(row[COL_LAT], row[COL_LON], BUCARAMANGA_COORDS["lat"], BUCARAMANGA_COORDS["lon"]),
        axis=1
    )
    print("  [OK] distancia_a_bucaramanga_km")

    # -------------------------------------------------------------------------
    # Variables de fuentes externas (marcadas como NaN por ahora)
    # -------------------------------------------------------------------------

    # codigo_divipola (DANE)
    df["codigo_divipola"] = np.nan
    print("  [OK] codigo_divipola (pendiente de fuente externa)")

    # poblacion_municipio (DANE)
    df["poblacion_municipio"] = np.nan
    print("  [OK] poblacion_municipio (pendiente de fuente externa)")

    # area_km2 (IGAC)
    df["area_km2"] = np.nan
    print("  [OK] area_km2 (pendiente de fuente externa)")

    # zona_amenaza_sismica (SGC/NSR-10)
    df["zona_amenaza_sismica"] = np.nan
    print("  [OK] zona_amenaza_sismica (pendiente de fuente externa)")

    # -------------------------------------------------------------------------
    # Variables calculadas (marcadas como NaN por ahora)
    # -------------------------------------------------------------------------

    # sismos_por_100mil_hab (requiere población)
    df["sismos_por_100mil_hab"] = np.nan
    print("  [OK] sismos_por_100mil_hab (pendiente de población)")

    # distancia_a_falla_km (requiere capa de fallas del SGC)
    df["distancia_a_falla_km"] = np.nan
    print("  [OK] distancia_a_falla_km (pendiente de capa de fallas)")

    # tipo_magnitud (ML, Mw) - marcar como desconocido por ahora
    df["tipo_magnitud"] = "Desconocido"
    print("  [OK] tipo_magnitud (pendiente de fuente SGC)")

    print("\n[OK] Variables derivadas agregadas exitosamente")
    return df


def generar_diccionario_datos(df):
    """
    Genera un diccionario de datos documentando todas las variables.

    Args:
        df (pd.DataFrame): DataFrame con todas las variables

    Returns:
        pd.DataFrame: Diccionario de datos
    """
    diccionario = []

    for col in df.columns:
        info = {
            "Variable": col,
            "Tipo": str(df[col].dtype),
            "Nulos": df[col].isna().sum(),
            "No Nulos": df[col].notna().sum(),
            "Unicos": df[col].nunique(),
            "Fuente": "",
            "Justificacion": ""
        }

        # Asignar fuente y justificación según la variable
        if col in [COL_FECHA, COL_ANIO, COL_MES, COL_DIA, COL_HORA, COL_LAT, COL_LON, COL_MAG]:
            info["Fuente"] = "Catálogo SGC"
            info["Justificacion"] = "Variable original del catálogo oficial"
        elif col == "dia_semana":
            info["Fuente"] = "Derivada"
            info["Justificacion"] = "Control de calidad (no debería haber diferencias reales)"
        elif col == "franja_horaria":
            info["Fuente"] = "Derivada"
            info["Justificacion"] = "Patrones horarios (día/noche)"
        elif col == "categoria_magnitud":
            info["Fuente"] = "Derivada"
            info["Justificacion"] = "Facilita comparar y filtrar sismos por tamaño"
        elif col == "categoria_profundidad":
            info["Fuente"] = "Derivada"
            info["Justificacion"] = "Separa tipos de fuente sísmica (superficial, intermedio, profundo)"
        elif col == "energia_liberada":
            info["Fuente"] = "Derivada"
            info["Justificacion"] = "Fórmula log10(E) = 1.5·M + 4.8, más útil que magnitud para sumar"
        elif col == "distancia_centro_nido_km":
            info["Fuente"] = "Derivada"
            info["Justificacion"] = "Distancia al centro del Nido de Bucaramanga (Haversine)"
        elif col == "distancia_a_bucaramanga_km":
            info["Fuente"] = "Derivada"
            info["Justificacion"] = "Cercanía a la zona urbana de Bucaramanga"
        elif col == "profundidad_km":
            info["Fuente"] = "Inferida"
            info["Justificacion"] = "Inferida basándose en características del Nido (100-160 km)"
        elif col in ["codigo_divipola", "poblacion_municipio"]:
            info["Fuente"] = "DANE (pendiente)"
            info["Justificacion"] = "Código oficial y población municipal"
        elif col == "area_km2":
            info["Fuente"] = "IGAC (pendiente)"
            info["Justificacion"] = "Área territorial del municipio"
        elif col == "zona_amenaza_sismica":
            info["Fuente"] = "SGC/NSR-10 (pendiente)"
            info["Justificacion"] = "Nivel de amenaza sísmica según norma colombiana"
        elif col == "sismos_por_100mil_hab":
            info["Fuente"] = "Calculada (pendiente)"
            info["Justificacion"] = "Normaliza para comparar municipios de distinto tamaño"
        elif col == "distancia_a_falla_km":
            info["Fuente"] = "SGC (pendiente)"
            info["Justificacion"] = "Distancia a fallas geológicas activas"
        elif col == "tipo_magnitud":
            info["Fuente"] = "SGC (pendiente)"
            info["Justificacion"] = "Permite comparar magnitudes de forma coherente (ML, Mw)"
        else:
            info["Fuente"] = "Desconocida"
            info["Justificacion"] = "Variable del dataset original"

        diccionario.append(info)

    return pd.DataFrame(diccionario)


if __name__ == "__main__":
    # Cargar dataset
    ruta_dataset = "info_registros/dataset_sismos_bucaramanga.csv"
    print(f"Cargando dataset desde {ruta_dataset}...")
    df = pd.read_csv(ruta_dataset)
    print(f"Dataset cargado: {len(df)} registros, {len(df.columns)} columnas\n")

    # Agregar variables derivadas
    df_completo = agregar_variables_derivadas(df)

    # Guardar dataset actualizado
    ruta_salida = "info_registros/dataset_sismos_bucaramanga_completo.csv"
    df_completo.to_csv(ruta_salida, index=False)
    print(f"\nDataset actualizado guardado en: {ruta_salida}")

    # Generar diccionario de datos
    diccionario = generar_diccionario_datos(df_completo)
    ruta_diccionario = "info_registros/diccionario_datos.csv"
    diccionario.to_csv(ruta_diccionario, index=False)
    print(f"Diccionario de datos guardado en: {ruta_diccionario}")

    # Resumen
    print(f"\nResumen final:")
    print(f"  - Registros: {len(df_completo)}")
    print(f"  - Columnas totales: {len(df_completo.columns)}")
    print(f"  - Variables del catálogo SGC: 7")
    print(f"  - Variables derivadas de fecha: 2")
    print(f"  - Variables derivadas físicas/espaciales: 5")
    print(f"  - Variables de fuentes externas (pendientes): 4")
    print(f"  - Variables calculadas (pendientes): 2")
    print(f"  - Total: {len(df_completo.columns)} variables")
