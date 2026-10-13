"""
Módulo de visualización para datos sísmicos del Nido de Bucaramanga.
Contiene 13 funciones para generar gráficos interactivos con Plotly.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# ============================================================================
# SECCIÓN 1: CONFIGURACIÓN DE COLUMNAS
# ============================================================================
# Ajusta estos nombres para que coincidan con tu dataset
COL_FECHA = "Fecha_Hora_Completa"
COL_ANIO = "Año"
COL_MES = "Mes"
COL_DIA = "Dia"
COL_HORA = "Hora"
COL_LAT = "Latitud"
COL_LON = "Longitud"
COL_MAG = "Magnitud"
COL_PROFUNDIDAD = "profundidad_km"  # Variable a agregar
COL_TIPO_MAG = "tipo_magnitud"  # Variable a agregar
COL_CATEGORIA_MAG = "categoria_magnitud"  # Variable a agregar
COL_CATEGORIA_PROF = "categoria_profundidad"  # Variable a agregar
COL_ENERGIA = "energia_liberada"  # Variable a agregar
COL_DIST_NIDO = "distancia_centro_nido_km"  # Variable a agregar
COL_DIST_BGA = "distancia_a_bucaramanga_km"  # Variable a agregar
COL_MUNICIPIO = "Municipio_Epicentral"
COL_DEPARTAMENTO = "Departamento_Reporte"
COL_AREA_EPICENTRAL = "Area_Epicentral"

# Coordenadas del centro del Nido de Bucaramanga
NIDO_CENTER = {"lat": 6.7, "lon": -73.2}
BUCARAMANGA_COORDS = {"lat": 7.125, "lon": -73.119}


# ============================================================================
# SECCIÓN 2: FUNCIONES DE UTILIDAD
# ============================================================================

def cargar_datos(ruta_archivo):
    """
    Carga datos sísmicos desde un archivo CSV o Excel.

    Args:
        ruta_archivo (str): Ruta al archivo (.csv o .xlsx)

    Returns:
        pd.DataFrame: DataFrame con los datos cargados
    """
    if ruta_archivo.endswith('.csv'):
        df = pd.read_csv(ruta_archivo)
    elif ruta_archivo.endswith('.xlsx'):
        df = pd.read_excel(ruta_archivo)
    else:
        raise ValueError("Formato no soportado. Usa .csv o .xlsx")

    # Convertir columnas numéricas
    for col in [COL_MAG, COL_LAT, COL_LON, COL_ANIO, COL_MES, COL_DIA, COL_HORA]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Convertir fecha si existe
    if COL_FECHA in df.columns:
        df[COL_FECHA] = pd.to_datetime(df[COL_FECHA], errors='coerce')

    return df


def filtrar(df, municipio=None, anio_ini=None, anio_fin=None, mag_min=None, mag_max=None):
    """
    Filtra el dataset según múltiples criterios.

    Args:
        df (pd.DataFrame): DataFrame original
        municipio (str): Filtrar por municipio (opcional)
        anio_ini (int): Año inicial (opcional)
        anio_fin (int): Año final (opcional)
        mag_min (float): Magnitud mínima (opcional)
        mag_max (float): Magnitud máxima (opcional)

    Returns:
        pd.DataFrame: DataFrame filtrado
    """
    df_filtrado = df.copy()

    if municipio and COL_MUNICIPIO in df.columns:
        df_filtrado = df_filtrado[df_filtrado[COL_MUNICIPIO].str.contains(municipio, case=False, na=False)]

    if anio_ini and COL_ANIO in df.columns:
        df_filtrado = df_filtrado[df_filtrado[COL_ANIO] >= anio_ini]

    if anio_fin and COL_ANIO in df.columns:
        df_filtrado = df_filtrado[df_filtrado[COL_ANIO] <= anio_fin]

    if mag_min and COL_MAG in df.columns:
        df_filtrado = df_filtrado[df_filtrado[COL_MAG] >= mag_min]

    if mag_max and COL_MAG in df.columns:
        df_filtrado = df_filtrado[df_filtrado[COL_MAG] <= mag_max]

    return df_filtrado


# ============================================================================
# SECCIÓN 3: FUNCIONES DE VISUALIZACIÓN
# ============================================================================

def grafico_sismos_por_anio(df, municipio=None):
    """
    Gráfico de barras: número de sismos por año.
    Puede filtrar por municipio específico.

    Args:
        df (pd.DataFrame): DataFrame con datos sísmicos
        municipio (str): Nombre del municipio para filtrar (opcional)

    Returns:
        plotly.graph_objects.Figure: Figura interactiva
    """
    df_filtrado = filtrar(df, municipio=municipio) if municipio else df

    if COL_ANIO not in df_filtrado.columns:
        raise ValueError(f"Columna {COL_ANIO} no encontrada en el dataset")

    conteo = df_filtrado[COL_ANIO].value_counts().sort_index()
    titulo = f"Sismos por año - {municipio}" if municipio else "Sismos por año"

    fig = px.bar(
        x=conteo.index,
        y=conteo.values,
        labels={'x': 'Año', 'y': 'Número de sismos'},
        title=titulo,
        color=conteo.values,
        color_continuous_scale='Viridis'
    )

    fig.update_layout(xaxis_type='category')
    return fig


def ranking_zonas(df, por_habitante=False, top_n=10):
    """
    Gráfico de barras horizontales: ranking de zonas/municipios.
    Puede ser absoluto o normalizado por 100.000 habitantes.

    Args:
        df (pd.DataFrame): DataFrame con datos sísmicos
        por_habitante (bool): Si True, normaliza por población
        top_n (int): Número de zonas a mostrar

    Returns:
        plotly.graph_objects.Figure: Figura interactiva
    """
    if COL_MUNICIPIO not in df.columns:
        raise ValueError(f"Columna {COL_MUNICIPIO} no encontrada en el dataset")

    conteo = df[COL_MUNICIPIO].value_counts().head(top_n)

    if por_habitante and 'poblacion_municipio' in df.columns:
        # Normalizar por población si existe la columna
        poblacion = df.groupby(COL_MUNICIPIO)['poblacion_municipio'].first()
        conteo = (conteo / poblacion * 100000).sort_values(ascending=True)
        y_label = "Sismos por 100.000 habitantes"
        titulo = f"Ranking de municipios (por 100.000 hab)"
    else:
        conteo = conteo.sort_values(ascending=True)
        y_label = "Número de sismos"
        titulo = f"Ranking de municipios (absoluto)"

    fig = px.bar(
        x=conteo.values,
        y=conteo.index,
        orientation='h',
        labels={'x': y_label, 'y': 'Municipio'},
        title=titulo,
        color=conteo.values,
        color_continuous_scale='Plasma'
    )

    return fig


def mapa_sismos(df, color_por="magnitud", tipo="puntos"):
    """
    Mapa interactivo de sismos.
    Puede ser de puntos o de calor.

    Args:
        df (pd.DataFrame): DataFrame con datos sísmicos
        color_por (str): Variable para colorear ("magnitud" o "profundidad")
        tipo (str): Tipo de mapa ("puntos" o "calor")

    Returns:
        plotly.graph_objects.Figure: Figura interactiva
    """
    if COL_LAT not in df.columns or COL_LON not in df.columns:
        raise ValueError(f"Columnas {COL_LAT} y {COL_LON} requeridas")

    color_col = COL_MAG if color_por == "magnitud" else COL_PROFUNDIDAD

    if tipo == "puntos":
        fig = px.scatter_geo(
            df,
            lat=COL_LAT,
            lon=COL_LON,
            color=color_col,
            size=COL_MAG if COL_MAG in df.columns else None,
            hover_data=[COL_MAG, COL_MUNICIPIO] if COL_MUNICIPIO in df.columns else [COL_MAG],
            color_continuous_scale='Reds' if color_por == "magnitud" else 'Blues',
            projection="mercator",
            scope="south america",
            title=f"Mapa de sismos (color por {color_por})"
        )
        fig.update_geos(
            center=dict(lat=NIDO_CENTER["lat"], lon=NIDO_CENTER["lon"]),
            projection_scale=15
        )
    else:  # calor
        fig = px.density_heatmap(
            df,
            x=COL_LON,
            y=COL_LAT,
            z=color_col if color_col in df.columns else COL_MAG,
            title=f"Mapa de calor - {color_por}",
            labels={"x": "Longitud", "y": "Latitud"},
            color_continuous_scale='Viridis'
        )
        fig.update_yaxes(autorange="reversed")  # Latitud crece hacia arriba

    return fig


def heatmap_mes_anio(df):
    """
    Mapa de calor: sismos por mes y año.

    Args:
        df (pd.DataFrame): DataFrame con datos sísmicos

    Returns:
        plotly.graph_objects.Figure: Figura interactiva
    """
    if COL_ANIO not in df.columns or COL_MES not in df.columns:
        raise ValueError(f"Columnas {COL_ANIO} y {COL_MES} requeridas")

    # Crear tabla de contingencia
    heatmap_data = df.groupby([COL_ANIO, COL_MES]).size().unstack(fill_value=0)

    fig = px.imshow(
        heatmap_data,
        labels=dict(x="Mes", y="Año", color="Sismos"),
        x=["Ene", "Feb", "Mar", "Abr", "May", "Jun",
           "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"],
        title="Sismos por mes y año",
        color_continuous_scale='YlOrRd',
        aspect="auto"
    )

    return fig


def histograma_magnitud(df):
    """
    Histograma de magnitudes.

    Args:
        df (pd.DataFrame): DataFrame con datos sísmicos

    Returns:
        plotly.graph_objects.Figure: Figura interactiva
    """
    if COL_MAG not in df.columns:
        raise ValueError(f"Columna {COL_MAG} no encontrada en el dataset")

    fig = px.histogram(
        df,
        x=COL_MAG,
        nbins=30,
        title="Distribución de magnitudes",
        labels={'x': 'Magnitud', 'y': 'Frecuencia'},
        color_discrete_sequence=['#636EFA']
    )

    fig.update_layout(bargap=0.1)
    return fig


def histograma_profundidad(df):
    """
    Histograma de profundidades.

    Args:
        df (pd.DataFrame): DataFrame con datos sísmicos

    Returns:
        plotly.graph_objects.Figure: Figura interactiva
    """
    if COL_PROFUNDIDAD not in df.columns:
        raise ValueError(f"Columna {COL_PROFUNDIDAD} no encontrada en el dataset")

    fig = px.histogram(
        df,
        x=COL_PROFUNDIDAD,
        nbins=30,
        title="Distribución de profundidades",
        labels={'x': 'Profundidad (km)', 'y': 'Frecuencia'},
        color_discrete_sequence=['#00CC96']
    )

    fig.update_layout(bargap=0.1)
    return fig


def dispersion_mag_prof(df):
    """
    Gráfico de dispersión: magnitud vs profundidad.

    Args:
        df (pd.DataFrame): DataFrame con datos sísmicos

    Returns:
        plotly.graph_objects.Figure: Figura interactiva
    """
    if COL_MAG not in df.columns or COL_PROFUNDIDAD not in df.columns:
        raise ValueError(f"Columnas {COL_MAG} y {COL_PROFUNDIDAD} requeridas")

    fig = px.scatter(
        df,
        x=COL_PROFUNDIDAD,
        y=COL_MAG,
        title="Magnitud vs Profundidad",
        labels={'x': 'Profundidad (km)', 'y': 'Magnitud'},
        color=COL_MAG,
        color_continuous_scale='Viridis',
        opacity=0.6
    )

    fig.update_layout(xaxis=dict(autorange="reversed"))  # Profundidad crece hacia abajo
    return fig


def sismo_mas_fuerte_por_anio(df):
    """
    Gráfico de barras: sismo más fuerte por año.

    Args:
        df (pd.DataFrame): DataFrame con datos sísmicos

    Returns:
        plotly.graph_objects.Figure: Figura interactiva
    """
    if COL_ANIO not in df.columns or COL_MAG not in df.columns:
        raise ValueError(f"Columnas {COL_ANIO} y {COL_MAG} requeridas")

    # Encontrar el sismo más fuerte por año
    max_por_anio = df.loc[df.groupby(COL_ANIO)[COL_MAG].idxmax()]

    fig = px.bar(
        max_por_anio,
        x=COL_ANIO,
        y=COL_MAG,
        title="Sismo más fuerte por año",
        labels={'x': 'Año', 'y': 'Magnitud máxima'},
        color=COL_MAG,
        color_continuous_scale='Reds',
        hover_data=[COL_MUNICIPIO] if COL_MUNICIPIO in df.columns else None
    )

    fig.update_layout(xaxis_type='category')
    return fig


def comparar_periodos(df, periodo1, periodo2):
    """
    Compara dos periodos de tiempo.

    Args:
        df (pd.DataFrame): DataFrame con datos sísmicos
        periodo1 (tuple): (anio_inicio, anio_fin) del primer periodo
        periodo2 (tuple): (anio_inicio, anio_fin) del segundo periodo

    Returns:
        plotly.graph_objects.Figure: Figura interactiva
    """
    if COL_ANIO not in df.columns:
        raise ValueError(f"Columna {COL_ANIO} no encontrada en el dataset")

    p1_start, p1_end = periodo1
    p2_start, p2_end = periodo2

    df_p1 = df[(df[COL_ANIO] >= p1_start) & (df[COL_ANIO] <= p1_end)]
    df_p2 = df[(df[COL_ANIO] >= p2_start) & (df[COL_ANIO] <= p2_end)]

    # Comparar magnitudes
    fig = go.Figure()

    fig.add_trace(go.Box(
        y=df_p1[COL_MAG],
        name=f"Periodo {p1_start}-{p1_end}",
        boxpoints='all',
        jitter=0.3,
        pointpos=-1.8
    ))

    fig.add_trace(go.Box(
        y=df_p2[COL_MAG],
        name=f"Periodo {p2_start}-{p2_end}",
        boxpoints='all',
        jitter=0.3,
        pointpos=-1.8
    ))

    fig.update_layout(
        title=f"Comparación de magnitudes: {p1_start}-{p1_end} vs {p2_start}-{p2_end}",
        yaxis_title="Magnitud"
    )

    return fig


def serie_temporal_magnitud(df, municipio=None):
    """
    Gráfico de línea: serie temporal de magnitudes.

    Args:
        df (pd.DataFrame): DataFrame con datos sísmicos
        municipio (str): Filtrar por municipio (opcional)

    Returns:
        plotly.graph_objects.Figure: Figura interactiva
    """
    df_filtrado = filtrar(df, municipio=municipio) if municipio else df

    if COL_FECHA not in df_filtrado.columns or COL_MAG not in df_filtrado.columns:
        raise ValueError(f"Columnas {COL_FECHA} y {COL_MAG} requeridas")

    df_filtrado = df_filtrado.sort_values(COL_FECHA)

    fig = px.line(
        df_filtrado,
        x=COL_FECHA,
        y=COL_MAG,
        title=f"Serie temporal de magnitudes - {municipio}" if municipio else "Serie temporal de magnitudes",
        labels={'x': 'Fecha', 'y': 'Magnitud'},
        markers=True
    )

    return fig


def distribucion_categorias_magnitud(df):
    """
    Gráfico de barras: distribución de categorías de magnitud.

    Args:
        df (pd.DataFrame): DataFrame con datos sísmicos

    Returns:
        plotly.graph_objects.Figure: Figura interactiva
    """
    if COL_CATEGORIA_MAG not in df.columns:
        raise ValueError(f"Columna {COL_CATEGORIA_MAG} no encontrada en el dataset")

    conteo = df[COL_CATEGORIA_MAG].value_counts()

    fig = px.bar(
        x=conteo.index,
        y=conteo.values,
        title="Distribución de categorías de magnitud",
        labels={'x': 'Categoría', 'y': 'Número de sismos'},
        color=conteo.values,
        color_continuous_scale='Spectral'
    )

    return fig


def distribucion_categorias_profundidad(df):
    """
    Gráfico de barras: distribución de categorías de profundidad.

    Args:
        df (pd.DataFrame): DataFrame con datos sísmicos

    Returns:
        plotly.graph_objects.Figure: Figura interactiva
    """
    if COL_CATEGORIA_PROF not in df.columns:
        raise ValueError(f"Columna {COL_CATEGORIA_PROF} no encontrada en el dataset")

    conteo = df[COL_CATEGORIA_PROF].value_counts()

    fig = px.bar(
        x=conteo.index,
        y=conteo.values,
        title="Distribución de categorías de profundidad",
        labels={'x': 'Categoría', 'y': 'Número de sismos'},
        color=conteo.values,
        color_continuous_scale='Viridis'
    )

    return fig


# ============================================================================
# SECCIÓN 4: FUNCIÓN DE PRUEBA
# ============================================================================

if __name__ == "__main__":
    # Ejemplo de uso con datos sintéticos
    print("Generando datos sintéticos para prueba...")

    np.random.seed(42)
    n_sismos = 3000

    datos_sinteticos = {
        COL_FECHA: pd.date_range(start='2010-01-01', periods=n_sismos, freq='D'),
        COL_ANIO: np.random.randint(2010, 2027, n_sismos),
        COL_MES: np.random.randint(1, 13, n_sismos),
        COL_DIA: np.random.randint(1, 29, n_sismos),
        COL_HORA: np.random.randint(0, 24, n_sismos),
        COL_LAT: np.random.uniform(6.0, 7.5, n_sismos),
        COL_LON: np.random.uniform(-74.0, -72.5, n_sismos),
        COL_MAG: np.random.uniform(2.0, 7.0, n_sismos),
        COL_PROFUNDIDAD: np.random.uniform(0, 200, n_sismos),
        COL_MUNICIPIO: np.random.choice(['Bucaramanga', 'Girón', 'Floridablanca', 'Piedecuesta'], n_sismos),
        COL_CATEGORIA_MAG: np.random.choice(['Micro', 'Menor', 'Ligero', 'Moderado'], n_sismos),
        COL_CATEGORIA_PROF: np.random.choice(['Superficial', 'Intermedio', 'Profundo'], n_sismos)
    }

    df = pd.DataFrame(datos_sinteticos)

    print("Probando todas las funciones...")
    print(f"1. Sismos por año: {len(df)} registros")
    fig1 = grafico_sismos_por_anio(df)
    print("   ✓")

    print(f"2. Ranking de zonas: {len(df)} registros")
    fig2 = ranking_zonas(df)
    print("   ✓")

    print(f"3. Mapa de sismos (puntos): {len(df)} registros")
    fig3 = mapa_sismos(df, tipo="puntos")
    print("   ✓")

    print(f"4. Mapa de calor: {len(df)} registros")
    fig4 = mapa_sismos(df, tipo="calor")
    print("   ✓")

    print(f"5. Heatmap mes × año: {len(df)} registros")
    fig5 = heatmap_mes_anio(df)
    print("   ✓")

    print(f"6. Histograma magnitud: {len(df)} registros")
    fig6 = histograma_magnitud(df)
    print("   ✓")

    print(f"7. Histograma profundidad: {len(df)} registros")
    fig7 = histograma_profundidad(df)
    print("   ✓")

    print(f"8. Dispersión mag vs prof: {len(df)} registros")
    fig8 = dispersion_mag_prof(df)
    print("   ✓")

    print(f"9. Sismo más fuerte por año: {len(df)} registros")
    fig9 = sismo_mas_fuerte_por_anio(df)
    print("   ✓")

    print(f"10. Comparación de periodos: {len(df)} registros")
    fig10 = comparar_periodos(df, (2010, 2015), (2016, 2026))
    print("   ✓")

    print(f"11. Serie temporal magnitud: {len(df)} registros")
    fig11 = serie_temporal_magnitud(df)
    print("   ✓")

    print(f"12. Distribución categorías magnitud: {len(df)} registros")
    fig12 = distribucion_categorias_magnitud(df)
    print("   ✓")

    print(f"13. Distribución categorías profundidad: {len(df)} registros")
    fig13 = distribucion_categorias_profundidad(df)
    print("   ✓")

    print("\n✓ Todas las 13 funciones generaron figuras correctamente")
