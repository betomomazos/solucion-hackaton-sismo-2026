#!/bin/bash

echo "===================================="
echo "Instalación - Sistema Riesgo Sísmico"
echo "===================================="
echo ""

echo "1. Verificando Python..."
python3 --version
if [ $? -ne 0 ]; then
    echo "ERROR: Python no está instalado. Por favor instala Python 3.11+"
    exit 1
fi

echo ""
echo "2. Creando entorno virtual (opcional pero recomendado)..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "Advertencia: No se pudo crear el entorno virtual. Continuando con Python global..."
else
    echo "Entorno virtual creado exitosamente."
    echo "Activando entorno virtual..."
    source venv/bin/activate
fi

echo ""
echo "3. Instalando dependencias..."
pip install --upgrade pip
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "ERROR: No se pudieron instalar las dependencias."
    exit 1
fi

echo ""
echo "===================================="
echo "Instalación completada exitosamente!"
echo "===================================="
echo ""
echo "Para iniciar la aplicación:"
echo "  - Con entorno virtual: source venv/bin/activate, luego python app.py"
echo "  - Sin entorno virtual: python3 app.py"
echo ""
echo "La aplicación estará disponible en: http://localhost:5000"
echo ""
