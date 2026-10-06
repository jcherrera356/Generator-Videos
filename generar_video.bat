@echo off
setlocal enabledelayedexpansion

set "DIR=%~dp0"
set "FFMPEG_BIN=C:\Users\USUARIO\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin"
set "PATH=%PATH%;%FFMPEG_BIN%"

cd /d "%DIR%"

echo.
echo  De donde sacamos el dato?
echo  ------------------------------
echo   1. Wikipedia
echo   2. Banco local (facts_bank.json)
echo   3. Videojuegos (API de RAWG)
echo   4. Tendencias (Google Trends, ultimas 24h)
echo   5. Automatico (al azar entre Wikipedia y banco local)
echo.
set /p OPCION="Elige una opcion (1-5): "

if "%OPCION%"=="1" set "SOURCE=wikipedia"
if "%OPCION%"=="2" set "SOURCE=local"
if "%OPCION%"=="3" set "SOURCE=games"
if "%OPCION%"=="4" set "SOURCE=trending"
if "%OPCION%"=="5" set "SOURCE=auto"

if not defined SOURCE (
    echo Opcion invalida, se usa "automatico" por defecto.
    set "SOURCE=auto"
)

if "%SOURCE%"=="trending" (
    echo.
    echo  De que categoria?
    echo  ------------------------------
    echo   1. Cualquiera
    echo   2. Videojuegos
    echo   3. Noticias
    echo   4. Moda
    echo   5. Entretenimiento
    echo   6. Tecnologia
    echo   7. Deportes
    echo   8. Negocios
    echo   9. Salud
    echo   10. Ciencia
    echo.
    set /p OPCION_CAT="Elige una opcion (1-10): "

    if "!OPCION_CAT!"=="2" set "CATEGORIA=Videojuegos"
    if "!OPCION_CAT!"=="3" set "CATEGORIA=Noticias"
    if "!OPCION_CAT!"=="4" set "CATEGORIA=Moda"
    if "!OPCION_CAT!"=="5" set "CATEGORIA=Entretenimiento"
    if "!OPCION_CAT!"=="6" set "CATEGORIA=Tecnología"
    if "!OPCION_CAT!"=="7" set "CATEGORIA=Deportes"
    if "!OPCION_CAT!"=="8" set "CATEGORIA=Negocios"
    if "!OPCION_CAT!"=="9" set "CATEGORIA=Salud"
    if "!OPCION_CAT!"=="10" set "CATEGORIA=Ciencia"
)

python presentacion\cli.py %SOURCE% %CATEGORIA%

echo.
pause
