"""
Script para probar las funciones de graficos_sismos.py con el dataset real.
"""

from graficos_sismos import *
import pandas as pd

# Cargar dataset actualizado
ruta_dataset = "info_registros/dataset_sismos_bucaramanga_completo.csv"
print(f"Cargando dataset desde {ruta_dataset}...")
df = cargar_datos(ruta_dataset)
print(f"Dataset cargado: {len(df)} registros, {len(df.columns)} columnas\n")

# Mostrar columnas disponibles
print("Columnas disponibles:")
for i, col in enumerate(df.columns, 1):
    print(f"  {i}. {col}")
print()

# Probar funciones que no requieren profundidad
print("Probando funciones de visualizacion...\n")

try:
    print("1. Sismos por año")
    fig1 = grafico_sismos_por_anio(df)
    print("   [OK] Generado\n")
except Exception as e:
    print(f"   [ERROR] {e}\n")

try:
    print("2. Ranking de zonas (absoluto)")
    fig2 = ranking_zonas(df, por_habitante=False)
    print("   [OK] Generado\n")
except Exception as e:
    print(f"   [ERROR] {e}\n")

try:
    print("3. Mapa de sismos (puntos)")
    fig3 = mapa_sismos(df, color_por="magnitud", tipo="puntos")
    print("   [OK] Generado\n")
except Exception as e:
    print(f"   [ERROR] {e}\n")

try:
    print("4. Heatmap mes x año")
    fig4 = heatmap_mes_anio(df)
    print("   [OK] Generado\n")
except Exception as e:
    print(f"   [ERROR] {e}\n")

try:
    print("5. Histograma magnitud")
    fig5 = histograma_magnitud(df)
    print("   [OK] Generado\n")
except Exception as e:
    print(f"   [ERROR] {e}\n")

try:
    print("6. Histograma profundidad")
    fig6 = histograma_profundidad(df)
    print("   [OK] Generado\n")
except Exception as e:
    print(f"   [ERROR] {e}\n")

try:
    print("7. Dispersión magnitud vs profundidad")
    fig7 = dispersion_mag_prof(df)
    print("   [OK] Generado\n")
except Exception as e:
    print(f"   [ERROR] {e}\n")

try:
    print("8. Sismo más fuerte por año")
    fig8 = sismo_mas_fuerte_por_anio(df)
    print("   [OK] Generado\n")
except Exception as e:
    print(f"   [ERROR] {e}\n")

try:
    print("9. Comparación de periodos")
    fig9 = comparar_periodos(df, (2020, 2023), (2024, 2026))
    print("   [OK] Generado\n")
except Exception as e:
    print(f"   [ERROR] {e}\n")

try:
    print("10. Serie temporal magnitud")
    fig10 = serie_temporal_magnitud(df)
    print("   [OK] Generado\n")
except Exception as e:
    print(f"   [ERROR] {e}\n")

try:
    print("11. Distribución categorías magnitud")
    fig11 = distribucion_categorias_magnitud(df)
    print("   [OK] Generado\n")
except Exception as e:
    print(f"   [ERROR] {e}\n")

try:
    print("12. Distribución categorías profundidad")
    fig12 = distribucion_categorias_profundidad(df)
    print("   [OK] Generado\n")
except Exception as e:
    print(f"   [ERROR] {e}\n")

try:
    print("13. Mapa de calor")
    fig13 = mapa_sismos(df, color_por="magnitud", tipo="calor")
    print("   [OK] Generado\n")
except Exception as e:
    print(f"   [ERROR] {e}\n")

print("Prueba completada.")
