"""
Dashboard Avanzado - Nivel Avanzado
Flujo funcional y verificable con demostración de la priorización.
Flujo integrado y trazabilidad.

Este dashboard integra todas las funcionalidades:
- Clasificación de riesgo en tiempo real
- Visualización territorial interactiva
- Sistema de priorización de zonas
- Trazabilidad de decisiones
"""

import pandas as pd
import numpy as np
import streamlit as st
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import json

# Configuración de la página
st.set_page_config(
    page_title="Sistema de Clasificación de Riesgo Sísmico - Santander",
    page_icon="🌋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Colores por nivel de riesgo
COLORS = {
    'BAJO': '#2ecc71',
    'MEDIO': '#f1c40f',
    'ALTO': '#e67e22',
    'CRÍTICO': '#e74c3c'
}

@st.cache_data
def cargar_datos():
    """Carga los datos sísmicos y de riesgo."""
    df = pd.read_csv('data/sismic_data_clasificado.csv')
    df['fecha'] = pd.to_datetime(df['fecha'])
    riesgo_zonal = pd.read_csv('data/riesgo_zonal.csv')
    prediccion = pd.read_csv('data/prediccion_riesgo.csv')
    return df, riesgo_zonal, prediccion

def clasificar_riesgo(magnitud, profundidad):
    """Clasifica el riesgo sísmico."""
    if magnitud > 5.5 and profundidad < 50:
        return 'CRÍTICO'
    elif magnitud > 4.5 or profundidad < 50:
        return 'ALTO'
    elif magnitud >= 3.0 or profundidad <= 100:
        return 'MEDIO'
    else:
        return 'BAJO'

def calcular_prioridad_zona(riesgo_zonal):
    """
    Calcula la prioridad de atención por zona basado en múltiples factores.
    Retorna un DataFrame con prioridad ordenada.
    """
    prioridad = riesgo_zonal.copy()

    # Calcular score de prioridad (0-100)
    prioridad['score_prioridad'] = (
        (prioridad['indice_riesgo'] / 100) * 40 +           # Índice de riesgo
        (prioridad['eventos_criticos'] / prioridad['total_eventos']) * 30 +  # Eventos críticos
        (prioridad['mag_max'] / 7.0) * 20 +                 # Magnitud máxima
        (1 - prioridad['prof_min'] / 200) * 10              # Profundidad mínima
    )

    # Clasificar prioridad
    prioridad['nivel_prioridad'] = pd.cut(
        prioridad['score_prioridad'],
        bins=[0, 30, 50, 70, 100],
        labels=['BAJA', 'MEDIA', 'ALTA', 'CRÍTICA']
    )

    # Ordenar por prioridad
    prioridad = prioridad.sort_values('score_prioridad', ascending=False)

    return prioridad

def generar_trazabilidad(accion, detalles):
    """Genera un registro de trazabilidad para la acción."""
    registro = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'accion': accion,
        'detalles': detalles
    }
    return registro

def main():
    # Título principal
    st.title("🌋 Sistema de Clasificación de Riesgo Sísmico - Santander")
    st.markdown("---")

    # Cargar datos
    df, riesgo_zonal, prediccion = cargar_datos()

    # Sidebar - Navegación
    st.sidebar.title("Navegación")
    pagina = st.sidebar.radio(
        "Seleccionar vista:",
        ["📊 Dashboard Principal", "🗺️ Visualización Territorial",
         "⚠️ Clasificación en Tiempo Real", "📋 Sistema de Priorización",
         "🔍 Trazabilidad"]
    )

    # Inicializar trazabilidad en session_state
    if 'trazabilidad' not in st.session_state:
        st.session_state.trazabilidad = []

    # ==================== DASHBOARD PRINCIPAL ====================
    if pagina == "📊 Dashboard Principal":
        st.header("📊 Dashboard Principal")

        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Eventos", len(df))
        with col2:
            st.metric("Zonas Monitoreadas", len(riesgo_zonal))
        with col3:
            eventos_criticos = len(df[df['clasificacion'] == 'CRÍTICO'])
            st.metric("Eventos Críticos", eventos_criticos)
        with col4:
            max_riesgo = riesgo_zonal['indice_riesgo'].max()
            st.metric("Máx. Índice Riesgo", f"{max_riesgo:.2f}")

        st.markdown("---")

        # Gráficos
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Distribución de Niveles de Riesgo")
            fig, ax = plt.subplots(figsize=(8, 5))
            dist_riesgo = df['clasificacion'].value_counts()
            colors = [COLORS.get(cat, '#95a5a6') for cat in dist_riesgo.index]
            ax.bar(dist_riesgo.index, dist_riesgo.values, color=colors)
            ax.set_ylabel('Número de Eventos')
            ax.set_xlabel('Nivel de Riesgo')
            ax.grid(axis='y', alpha=0.3)
            st.pyplot(fig)

        with col2:
            st.subheader("Índice de Riesgo por Zona")
            fig, ax = plt.subplots(figsize=(8, 5))
            zonas_ordenadas = riesgo_zonal.sort_values('indice_riesgo', ascending=True)
            colores = [COLORS.get(riesgo, '#95a5a6') for riesgo in zonas_ordenadas['riesgo_zonal']]
            ax.barh(zonas_ordenadas['ubicacion'], zonas_ordenadas['indice_riesgo'], color=colores)
            ax.set_xlabel('Índice de Riesgo (0-100)')
            ax.grid(axis='x', alpha=0.3)
            st.pyplot(fig)

        # Predicción a 30 días
        st.subheader("📈 Predicción de Riesgo a 30 Días")
        prediccion_7dias = prediccion.head(7)
        st.dataframe(prediccion_7dias, use_container_width=True)

    # ==================== VISUALIZACIÓN TERRITORIAL ====================
    elif pagina == "🗺️ Visualización Territorial":
        st.header("🗺️ Visualización Territorial")

        # Mapa de riesgo
        st.subheader("Mapa de Riesgo por Municipio")
        center_lat, center_lon = 6.8, -73.1
        m = folium.Map(location=[center_lat, center_lon], zoom_start=9)

        for _, row in riesgo_zonal.iterrows():
            municipio = row['ubicacion']
            indice_riesgo = row['indice_riesgo']
            riesgo = row['riesgo_zonal']

            municipio_data = df[df['ubicacion'] == municipio]
            lat = municipio_data['latitud'].mean()
            lon = municipio_data['longitud'].mean()

            color = COLORS.get(riesgo, '#95a5a6')

            popup_content = f"""
            <div style="font-family: Arial; font-size: 12px;">
                <h4 style="color: {color};">{municipio}</h4>
                <p><b>Índice de Riesgo:</b> {indice_riesgo:.2f}/100</p>
                <p><b>Nivel:</b> {riesgo}</p>
                <p><b>Eventos Totales:</b> {row['total_eventos']}</p>
            </div>
            """

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

        st_folium(m, width=1200, height=500)

        # Tabla comparativa
        st.subheader("Comparación Detallada por Zona")
        tabla = riesgo_zonal[['ubicacion', 'indice_riesgo', 'riesgo_zonal',
                              'total_eventos', 'mag_promedio', 'mag_max']]
        tabla.columns = ['Municipio', 'Índice Riesgo', 'Nivel Riesgo',
                        'Total Eventos', 'Mag Promedio', 'Mag Máxima']
        st.dataframe(tabla, use_container_width=True)

    # ==================== CLASIFICACIÓN EN TIEMPO REAL ====================
    elif pagina == "⚠️ Clasificación en Tiempo Real":
        st.header("⚠️ Clasificación de Riesgo en Tiempo Real")

        st.markdown("""
        Ingrese los datos de un evento sísmico para obtener su clasificación de riesgo.
        """)

        col1, col2, col3 = st.columns(3)

        with col1:
            magnitud = st.number_input("Magnitud (Richter)", min_value=0.0, max_value=10.0,
                                      value=4.0, step=0.1)
        with col2:
            profundidad = st.number_input("Profundidad (km)", min_value=0.0, max_value=700.0,
                                         value=50.0, step=1.0)
        with col3:
            ubicacion = st.selectbox("Ubicación", df['ubicacion'].unique())

        if st.button("Clasificar Riesgo"):
            riesgo = clasificar_riesgo(magnitud, profundidad)

            # Mostrar resultado
            st.markdown("---")
            col1, col2 = st.columns([1, 2])

            with col1:
                st.metric("Nivel de Riesgo", riesgo)

            with col2:
                if riesgo == 'CRÍTICO':
                    st.error("⚠️ ¡ALERTA MÁXIMA! Evacuación inmediata recomendada.")
                elif riesgo == 'ALTO':
                    st.warning("🚨 Tomar medidas de precaución inmediatas.")
                elif riesgo == 'MEDIO':
                    st.info("ℹ️ Mantenerse informado y preparado.")
                else:
                    st.success("✅ Riesgo bajo, monitoreo normal.")

            # Registrar en trazabilidad
            registro = generar_trazabilidad(
                "CLASIFICACION_EVENTO",
                f"Magnitud: {magnitud}, Profundidad: {profundidad}km, Ubicación: {ubicacion}, Riesgo: {riesgo}"
            )
            st.session_state.trazabilidad.append(registro)

            # Comparación con eventos similares
            st.markdown("---")
            st.subheader("Eventos Históricos Similares")
            eventos_similares = df[
                (df['magnitud'].between(magnitud - 0.5, magnitud + 0.5)) &
                (df['profundidad'].between(profundidad - 20, profundidad + 20))
            ].head(10)

            if len(eventos_similares) > 0:
                st.dataframe(eventos_similares[['fecha', 'magnitud', 'profundidad',
                                                'ubicacion', 'clasificacion']],
                            use_container_width=True)
            else:
                st.info("No se encontraron eventos similares en la base de datos.")

    # ==================== SISTEMA DE PRIORIZACIÓN ====================
    elif pagina == "📋 Sistema de Priorización":
        st.header("📋 Sistema de Priorización de Zonas")

        st.markdown("""
        Este sistema calcula la prioridad de atención de cada zona basado en:
        - Índice de riesgo sísmico
        - Frecuencia de eventos críticos
        - Magnitud máxima histórica
        - Profundidad de los eventos
        """)

        # Calcular prioridad
        prioridad = calcular_prioridad_zona(riesgo_zonal)

        # Mostrar tabla de prioridad
        st.subheader("Ranking de Prioridad de Atención")
        tabla_prioridad = prioridad[['ubicacion', 'score_prioridad', 'nivel_prioridad',
                                      'indice_riesgo', 'eventos_criticos', 'total_eventos']]
        tabla_prioridad.columns = ['Municipio', 'Score Prioridad', 'Nivel Prioridad',
                                   'Índice Riesgo', 'Eventos Críticos', 'Total Eventos']
        st.dataframe(tabla_prioridad, use_container_width=True)

        # Gráfico de prioridad
        st.subheader("Visualización de Prioridad")
        fig, ax = plt.subplots(figsize=(10, 6))
        colores_prioridad = {
            'BAJA': '#2ecc71',
            'MEDIA': '#f1c40f',
            'ALTA': '#e67e22',
            'CRÍTICA': '#e74c3c'
        }
        colores = [colores_prioridad.get(p, '#95a5a6') for p in prioridad['nivel_prioridad']]
        ax.barh(prioridad['ubicacion'], prioridad['score_prioridad'], color=colores)
        ax.set_xlabel('Score de Prioridad (0-100)')
        ax.set_title('Prioridad de Atención por Municipio')
        ax.grid(axis='x', alpha=0.3)
        st.pyplot(fig)

        # Recomendaciones
        st.subheader("Recomendaciones por Nivel de Prioridad")
        st.markdown("""
        **🔴 CRÍTICA:**
        - Requiere monitoreo continuo 24/7
        - Planes de evacuación actualizados
        - Equipos de respuesta en sitio

        **🟠 ALTA:**
        - Monitoreo frecuente
        - Simulacros mensuales
        - Evaluación de infraestructura

        **🟡 MEDIA:**
        - Monitoreo regular
        - Simulacros trimestrales
        - Planes de contingencia

        **🟢 BAJA:**
        - Monitoreo estándar
        - Simulacros anuales
        - Mantenimiento de planes
        """)

        # Registrar vista en trazabilidad
        if st.button("Registrar Priorización"):
            registro = generar_trazabilidad(
                "PRIORIZACION_ZONAS",
                f"Priorización completada. Zona más crítica: {prioridad.iloc[0]['ubicacion']}"
            )
            st.session_state.trazabilidad.append(registro)
            st.success("Priorización registrada en trazabilidad.")

    # ==================== TRAZABILIDAD ====================
    elif pagina == "🔍 Trazabilidad":
        st.header("🔍 Trazabilidad del Sistema")

        st.markdown("""
        Registro de todas las acciones realizadas en el sistema para garantizar
        la trazabilidad y reproducibilidad de los análisis.
        """)

        if len(st.session_state.trazabilidad) == 0:
            st.info("No hay registros de trazabilidad aún. Realice acciones en el sistema para generar registros.")
        else:
            trazabilidad_df = pd.DataFrame(st.session_state.trazabilidad)
            st.dataframe(trazabilidad_df, use_container_width=True)

            # Exportar
            if st.button("Exportar Trazabilidad"):
                trazabilidad_df.to_csv('output/trazabilidad.csv', index=False)
                st.success("Trazabilidad exportada a output/trazabilidad.csv")

        # Botón para limpiar
        if st.button("Limpiar Trazabilidad"):
            st.session_state.trazabilidad = []
            st.success("Trazabilidad limpiada.")

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 12px;'>
        Sistema de Clasificación de Riesgo Sísmico - Santander<br>
        Hackathon CIAI 2026 | Datos simulados basados en información del SGC
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
