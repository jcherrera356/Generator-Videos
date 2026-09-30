@echo off
setlocal

set "DIR=%~dp0"
set "FFMPEG_BIN=C:\Users\USUARIO\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin"
set "PATH=%PATH%;%FFMPEG_BIN%"

cd /d "%DIR%"
python generate_video.py

echo.
pause
