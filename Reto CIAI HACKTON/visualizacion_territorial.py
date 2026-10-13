"""
Visualización Territorial - Nivel Medio
Prototipo funcional y visualización reproducible que compara unidades territoriales.

Este script crea un mapa interactivo de Santander mostrando el riesgo sísmico
por municipio, permitiendo comparar las diferentes unidades territoriales.
"""

import pandas as pd
import folium
from folium import plugins
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Cargar datos
df = pd.read_csv('data/sismic_data_clasificado.csv')
df['fecha'] = pd.to_datetime(df['fecha'])
riesgo_zonal = pd.read_csv('data/riesgo_zonal.csv')

# Configuración de colores por nivel de riesgo
COLORS = {
    'BAJO': '#2ecc71',      # Verde
    'MEDIO': '#f1c40f',     # Amarillo
    'ALTO': '#e67e22',      # Naranja
    'CRÍTICO': '#e74c3c'    # Rojo
}

def crear_mapa_riesgo_santander():
    """
    Crea un mapa interactivo de Santander con los niveles de riesgo sísmico por municipio.
    """
    # Coordenadas centrales de Santander
    center_lat = 6.8
    center_lon = -73.1

    # Crear mapa base
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=9,
        tiles='OpenStreetMap'
    )

    # Agregar título
    title_html = '''
        <h3 align="center" style="font-size:20px"><b>Riesgo Sísmico por Municipio - Santander</b></h3>
        <p align="center" style="font-size:12px">Índice de riesgo basado en magnitud, profundidad y frecuencia de eventos</p>
    '''
    m.get_root().html.add_child(folium.Element(title_html))

    # Agregar marcadores por municipio
    for _, row in riesgo_zonal.iterrows():
        municipio = row['ubicacion']
        indice_riesgo = row['indice_riesgo']
        riesgo = row['riesgo_zonal']

        # Obtener coordenadas promedio del municipio
        municipio_data = df[df['ubicacion'] == municipio]
        lat = municipio_data['latitud'].mean()
        lon = municipio_data['longitud'].mean()

        # Color según nivel de riesgo
        color = COLORS.get(riesgo, '#95a5a6')

        # Información del popup
        popup_content = f"""
        <div style="font-family: Arial; font-size: 12px;">
            <h4 style="color: {color};">{municipio}</h4>
            <p><b>Índice de Riesgo:</b> {indice_riesgo:.2f}/100</p>
            <p><b>Nivel:</b> {riesgo}</p>
            <p><b>Eventos Totales:</b> {row['total_eventos']}</p>
            <p><b>Mag. Promedio:</b> {row['mag_promedio']:.2f}</p>
            <p><b>Mag. Máxima:</b> {row['mag_max']:.2f}</p>
            <p><b>Prof. Promedio:</b> {row['prof_promedio']:.1f} km</p>
        </div>
        """

        # Agregar círculo con radio proporcional al índice de riesgo
        folium.CircleMarker(
            location=[lat, lon],
            radius=10 + (indice_riesgo / 5),
            popup=folium.Popup(popup_content, max_width=300),
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.6,
            weight=2
        ).add_to(m)

        # Agregar etiqueta del municipio
        folium.Marker(
            location=[lat, lon],
            icon=folium.DivIcon(
                html=f'<div style="font-size: 10px; font-weight: bold; color: #333;">{municipio}</div>',
                icon_size=(80, 20),
                icon_anchor=(40, 10)
            )
        ).add_to(m)

    # Agregar leyenda
    legend_html = '''
        <div style="position: fixed;
                    bottom: 50px; left: 50px; width: 150px; height: 140px;
                    background-color: white; border: 2px solid grey; z-index: 9999;
                    font-size: 12px; padding: 10px">
            <p style="font-weight: bold; margin: 0 0 10px 0;">Nivel de Riesgo</p>
            <p><i class="fa fa-circle" style="color: #2ecc71"></i> BAJO</p>
            <p><i class="fa fa-circle" style="color: #f1c40f"></i> MEDIO</p>
            <p><i class="fa fa-circle" style="color: #e67e22"></i> ALTO</p>
            <p><i class="fa fa-circle" style="color: #e74c3c"></i> CRÍTICO</p>
        </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    return m

def crear_mapa_calor_eventos():
    """
    Crea un mapa de calor con la ubicación de todos los eventos sísmicos.
    """
    center_lat = 6.8
    center_lon = -73.1

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=9,
        tiles='OpenStreetMap'
    )

    # Agregar título
    title_html = '''
        <h3 align="center" style="font-size:20px"><b>Mapa de Calor - Eventos Sísmicos</b></h3>
        <p align="center" style="font-size:12px">Distribución espacial de eventos sísmicos en Santander</p>
    '''
    m.get_root().html.add_child(folium.Element(title_html))

    # Preparar datos para el mapa de calor
    heat_data = [[row['latitud'], row['longitud'], row['magnitud']]
                 for _, row in df.iterrows()]

    # Agregar mapa de calor
    plugins.HeatMap(
        heat_data,
        min_opacity=0.4,
        max_zoom=12,
        radius=25,
        blur=20,
        gradient={0.2: 'blue', 0.4: 'lime', 0.6: 'orange', 1.0: 'red'}
    ).add_to(m)

    return m

def crear_graficos_comparativos():
    """
    Crea gráficos comparativos entre los diferentes municipios.
    """
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Comparación de Riesgo Sísmico por Municipio - Santander',
                 fontsize=16, fontweight='bold')

    # 1. Índice de riesgo por municipio
    ax1 = axes[0, 0]
    colores = [COLORS[riesgo] for riesgo in riesgo_zonal['riesgo_zonal']]
    ax1.bar(riesgo_zonal['ubicacion'], riesgo_zonal['indice_riesgo'], color=colores)
    ax1.set_title('Índice de Riesgo por Municipio', fontweight='bold')
    ax1.set_ylabel('Índice de Riesgo (0-100)')
    ax1.set_xlabel('Municipio')
    ax1.tick_params(axis='x', rotation=45)
    ax1.grid(axis='y', alpha=0.3)

    # 2. Magnitud promedio por municipio
    ax2 = axes[0, 1]
    ax2.bar(riesgo_zonal['ubicacion'], riesgo_zonal['mag_promedio'], color='steelblue')
    ax2.set_title('Magnitud Promedio por Municipio', fontweight='bold')
    ax2.set_ylabel('Magnitud')
    ax2.set_xlabel('Municipio')
    ax2.tick_params(axis='x', rotation=45)
    ax2.grid(axis='y', alpha=0.3)

    # 3. Total de eventos por municipio
    ax3 = axes[1, 0]
    ax3.bar(riesgo_zonal['ubicacion'], riesgo_zonal['total_eventos'], color='coral')
    ax3.set_title('Total de Eventos por Municipio', fontweight='bold')
    ax3.set_ylabel('Número de Eventos')
    ax3.set_xlabel('Municipio')
    ax3.tick_params(axis='x', rotation=45)
    ax3.grid(axis='y', alpha=0.3)

    # 4. Distribución de magnitudes
    ax4 = axes[1, 1]
    for municipio in riesgo_zonal['ubicacion']:
        data = df[df['ubicacion'] == municipio]['magnitud']
        ax4.hist(data, alpha=0.5, label=municipio, bins=15)
    ax4.set_title('Distribución de Magnitudes por Municipio', fontweight='bold')
    ax4.set_xlabel('Magnitud')
    ax4.set_ylabel('Frecuencia')
    ax4.legend()
    ax4.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    return fig

def crear_tabla_comparativa():
    """
    Crea una tabla comparativa detallada de los municipios.
    """
    # Ordenar por índice de riesgo
    tabla = riesgo_zonal.sort_values('indice_riesgo', ascending=False).copy()

    # Formatear para visualización
    tabla['mag_promedio'] = tabla['mag_promedio'].round(2)
    tabla['mag_max'] = tabla['mag_max'].round(2)
    tabla['prof_promedio'] = tabla['prof_promedio'].round(1)
    tabla['indice_riesgo'] = tabla['indice_riesgo'].round(2)

    # Renombrar columnas
    tabla.columns = ['Municipio', 'Mag Promedio', 'Mag Máxima', 'Desv Mag',
                     'Prof Promedio', 'Prof Mín', 'Eventos Críticos',
                     'Total Eventos', 'Índice Riesgo', 'Nivel Riesgo']

    return tabla[['Municipio', 'Índice Riesgo', 'Nivel Riesgo', 'Total Eventos',
                  'Mag Promedio', 'Mag Máxima', 'Prof Promedio', 'Eventos Críticos']]

if __name__ == "__main__":
    print("Generando visualización territorial...")

    # Crear mapa de riesgo
    mapa_riesgo = crear_mapa_riesgo_santander()
    mapa_riesgo.save('output/mapa_riesgo_santander.html')
    print("[OK] Mapa de riesgo guardado: output/mapa_riesgo_santander.html")

    # Crear mapa de calor
    mapa_calor = crear_mapa_calor_eventos()
    mapa_calor.save('output/mapa_calor_eventos.html')
    print("[OK] Mapa de calor guardado: output/mapa_calor_eventos.html")

    # Crear gráficos comparativos
    fig = crear_graficos_comparativos()
    fig.savefig('output/graficos_comparativos.png', dpi=150, bbox_inches='tight')
    print("[OK] Graficos comparativos guardados: output/graficos_comparativos.png")

    # Crear tabla comparativa
    tabla = crear_tabla_comparativa()
    tabla.to_csv('output/tabla_comparativa.csv', index=False)
    print("[OK] Tabla comparativa guardada: output/tabla_comparativa.csv")

    print("\nTabla comparativa:")
    print(tabla.to_string(index=False))

    print("\n[OK] Visualizacion territorial completada exitosamente.")
