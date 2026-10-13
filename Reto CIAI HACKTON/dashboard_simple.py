"""
Dashboard Simplificado - Nivel Avanzado
Versión simplificada sin dependencias complejas de mapas interactivos.
"""

import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

# Configuracion de la pagina
st.set_page_config(
    page_title="Sistema de Riesgo Sismico - Santander",
    layout="wide"
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

def main():
    st.title("Sistema de Clasificacion de Riesgo Sismico - Santander")
    st.markdown("---")

    # Cargar datos
    df, riesgo_zonal, prediccion = cargar_datos()

    # Sidebar
    st.sidebar.title("Navegacion")
    pagina = st.sidebar.radio(
        "Seleccionar vista:",
        ["Dashboard", "Clasificacion", "Priorizacion", "Analisis"]
    )

    # Inicializar trazabilidad
    if 'trazabilidad' not in st.session_state:
        st.session_state.trazabilidad = []

    # ==================== DASHBOARD ====================
    if pagina == "Dashboard":
        st.header("Dashboard Principal")

        # Métricas
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Eventos", len(df))
        with col2:
            st.metric("Zonas", len(riesgo_zonal))
        with col3:
            st.metric("Eventos Críticos", len(df[df['clasificacion'] == 'CRÍTICO']))
        with col4:
            st.metric("Max Índice Riesgo", f"{riesgo_zonal['indice_riesgo'].max():.2f}")

        st.markdown("---")

        # Gráficos
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Distribución de Riesgo")
            fig, ax = plt.subplots(figsize=(8, 5))
            dist_riesgo = df['clasificacion'].value_counts()
            colors = [COLORS.get(cat, '#95a5a6') for cat in dist_riesgo.index]
            ax.bar(dist_riesgo.index, dist_riesgo.values, color=colors)
            ax.set_ylabel('Eventos')
            ax.set_xlabel('Nivel de Riesgo')
            ax.grid(axis='y', alpha=0.3)
            st.pyplot(fig)

        with col2:
            st.subheader("Índice de Riesgo por Zona")
            fig, ax = plt.subplots(figsize=(8, 5))
            zonas_ordenadas = riesgo_zonal.sort_values('indice_riesgo', ascending=True)
            colores = [COLORS.get(riesgo, '#95a5a6') for riesgo in zonas_ordenadas['riesgo_zonal']]
            ax.barh(zonas_ordenadas['ubicacion'], zonas_ordenadas['indice_riesgo'], color=colores)
            ax.set_xlabel('Índice de Riesgo')
            ax.grid(axis='x', alpha=0.3)
            st.pyplot(fig)

        # Tabla de zonas
        st.subheader("Resumen por Zona")
        tabla = riesgo_zonal[['ubicacion', 'indice_riesgo', 'riesgo_zonal',
                              'total_eventos', 'mag_promedio', 'mag_max']]
        tabla.columns = ['Municipio', 'Índice Riesgo', 'Nivel', 'Eventos', 'Mag Prom', 'Mag Max']
        st.dataframe(tabla, use_container_width=True)

    # ==================== CLASIFICACION ====================
    elif pagina == "Clasificacion":
        st.header("Clasificacion en Tiempo Real")

        col1, col2, col3 = st.columns(3)
        with col1:
            magnitud = st.number_input("Magnitud", 0.0, 10.0, 4.0, 0.1)
        with col2:
            profundidad = st.number_input("Profundidad (km)", 0.0, 700.0, 50.0, 1.0)
        with col3:
            ubicacion = st.selectbox("Ubicación", df['ubicacion'].unique())

        if st.button("Clasificar"):
            riesgo = clasificar_riesgo(magnitud, profundidad)

            st.markdown("---")
            col1, col2 = st.columns([1, 2])

            with col1:
                st.metric("Nivel de Riesgo", riesgo)

            with col2:
                if riesgo == 'CRITICO':
                    st.error("ALERTA MAXIMA! Evacuacion inmediata.")
                elif riesgo == 'ALTO':
                    st.warning("Medidas de precaucion inmediatas.")
                elif riesgo == 'MEDIO':
                    st.info("Mantenerse informado y preparado.")
                else:
                    st.success("Riesgo bajo, monitoreo normal.")

            # Registrar
            st.session_state.trazabilidad.append({
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'accion': 'CLASIFICACION',
                'magnitud': magnitud,
                'profundidad': profundidad,
                'ubicacion': ubicacion,
                'riesgo': riesgo
            })

            # Eventos similares
            st.markdown("---")
            st.subheader("Eventos Similares")
            similares = df[
                (df['magnitud'].between(magnitud - 0.5, magnitud + 0.5)) &
                (df['profundidad'].between(profundidad - 20, profundidad + 20))
            ].head(10)

            if len(similares) > 0:
                st.dataframe(similares[['fecha', 'magnitud', 'profundidad',
                                       'ubicacion', 'clasificacion']],
                            use_container_width=True)
            else:
                st.info("No hay eventos similares.")

    # ==================== PRIORIZACION ====================
    elif pagina == "Priorizacion":
        st.header("Sistema de Priorizacion")

        st.markdown("""
        Priorización basada en: índice de riesgo, eventos críticos, magnitud máxima.
        """)

        # Calcular prioridad
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
            labels=['BAJA', 'MEDIA', 'ALTA', 'CRÍTICA']
        )
        prioridad = prioridad.sort_values('score_prioridad', ascending=False)

        # Tabla
        st.subheader("Ranking de Prioridad")
        tabla_prioridad = prioridad[['ubicacion', 'score_prioridad', 'nivel_prioridad',
                                      'indice_riesgo', 'eventos_criticos']]
        tabla_prioridad.columns = ['Municipio', 'Score', 'Nivel', 'Índice Riesgo', 'Críticos']
        st.dataframe(tabla_prioridad, use_container_width=True)

        # Gráfico
        st.subheader("Visualización de Prioridad")
        fig, ax = plt.subplots(figsize=(10, 6))
        colores = {
            'BAJA': '#2ecc71', 'MEDIA': '#f1c40f',
            'ALTA': '#e67e22', 'CRÍTICA': '#e74c3c'
        }
        colors = [colores.get(p, '#95a5a6') for p in prioridad['nivel_prioridad']]
        ax.barh(prioridad['ubicacion'], prioridad['score_prioridad'], color=colors)
        ax.set_xlabel('Score de Prioridad')
        ax.grid(axis='x', alpha=0.3)
        st.pyplot(fig)

        # Recomendaciones
        st.subheader("Recomendaciones")
        st.markdown("""
        **CRITICA:** Monitoreo 24/7, planes de evacuacion, equipos en sitio.
        **ALTA:** Monitoreo frecuente, simulacros mensuales, evaluacion de infraestructura.
        **MEDIA:** Monitoreo regular, simulacros trimestrales, planes de contingencia.
        **BAJA:** Monitoreo estandar, simulacros anuales, mantenimiento de planes.
        """)

    # ==================== ANALISIS ====================
    elif pagina == "Analisis":
        st.header("Analisis Detallado")

        # Trazabilidad
        st.subheader("Trazabilidad de Acciones")
        if len(st.session_state.trazabilidad) > 0:
            trazabilidad_df = pd.DataFrame(st.session_state.trazabilidad)
            st.dataframe(trazabilidad_df, use_container_width=True)
        else:
            st.info("No hay registros de trazabilidad aún.")

        # Prediccion
        st.subheader("Prediccion a 7 Dias")
        st.dataframe(prediccion.head(7), use_container_width=True)

        # Estadisticas
        st.subheader("Estadisticas por Zona")
        stats = df.groupby('ubicacion').agg({
            'magnitud': ['mean', 'max', 'std'],
            'profundidad': 'mean',
            'clasificacion': lambda x: (x == 'CRÍTICO').sum()
        }).round(2)
        stats.columns = ['Mag Prom', 'Mag Max', 'Desv Mag', 'Prof Prom', 'Críticos']
        st.dataframe(stats, use_container_width=True)

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 12px;'>
        Sistema de Clasificación de Riesgo Sísmico - Santander<br>
        Hackathon CIAI 2026
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
