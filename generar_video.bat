@echo off
setlocal

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
echo   4. Automatico (al azar entre Wikipedia y banco local)
echo.
set /p OPCION="Elige una opcion (1-4): "

if "%OPCION%"=="1" set "SOURCE=wikipedia"
if "%OPCION%"=="2" set "SOURCE=local"
if "%OPCION%"=="3" set "SOURCE=games"
if "%OPCION%"=="4" set "SOURCE=auto"

if not defined SOURCE (
    echo Opcion invalida, se usa "automatico" por defecto.
    set "SOURCE=auto"
)

python generate_video.py %SOURCE%

echo.
pause
