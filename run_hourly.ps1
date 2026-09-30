$ErrorActionPreference = "Stop"

$dir = "C:\Users\USUARIO\Documents\ChicoTuf\generador-videos"
Set-Location $dir

$ffmpegBin = "C:\Users\USUARIO\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin"
if ($env:Path -notlike "*$ffmpegBin*") {
    $env:Path += ";$ffmpegBin"
}

$logFile = Join-Path $dir "generation.log"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $logFile -Value "----- $timestamp -----" -Encoding utf8

python generate_video.py 2>&1 | Out-File -FilePath $logFile -Append -Encoding utf8
