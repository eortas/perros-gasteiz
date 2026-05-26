@echo off
cd /d "%~dp0"
echo ====================================
echo  Scraper de Perros Vitoria-Gasteiz
echo ====================================
echo.

REM Verificar si existe la carpeta venv
if exist venv\Scripts\activate.bat (
    echo Activando entorno virtual...
    call venv\Scripts\activate.bat
) else (
    echo Instalando dependencias...
    pip install -r requirements.txt
)

echo.
echo Ejecutando scraper...
python scraper.py

echo.
echo Proceso completado.
pause