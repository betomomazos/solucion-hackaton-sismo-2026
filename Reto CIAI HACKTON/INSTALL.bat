@echo off
echo ====================================
echo Instalacion - Sistema Riesgo Sismico
echo ====================================
echo.

echo 1. Verificando Python...
python --version
if errorlevel 1 (
    echo ERROR: Python no esta instalado. Por favor instala Python 3.11+ desde https://www.python.org/downloads/
    pause
    exit /b 1
)

echo.
echo 2. Creando entorno virtual (opcional pero recomendado)...
python -m venv venv
if errorlevel 1 (
    echo Advertencia: No se pudo crear el entorno virtual. Continuando con Python global...
) else (
    echo Entorno virtual creado exitosamente.
    echo Activando entorno virtual...
    call venv\Scripts\activate
)

echo.
echo 3. Instalando dependencias...
pip install --upgrade pip
pip install -r requirements.txt

if errorlevel 1 (
    echo ERROR: No se pudieron instalar las dependencias.
    pause
    exit /b 1
)

echo.
echo ====================================
echo Instalacion completada exitosamente!
echo ====================================
echo.
echo Para iniciar la aplicacion:
echo   - Con entorno virtual: llamar venv\Scripts\activate.bat, luego python app.py
echo   - Sin entorno virtual: python app.py
echo.
echo La aplicacion estara disponible en: http://localhost:5000
echo.
pause
