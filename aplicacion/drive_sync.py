"""
Capa de aplicación: sube el video generado (y su caption) a una carpeta de
Google Drive.

El registro de "no repetir" ya no pasa por acá -- antes vivía en archivos
used_*.json que se subían/bajaban de Drive en cada corrida, lo que podía
perder datos si dos equipos generaban video casi al mismo tiempo (uno
pisaba el progreso del otro). Ahora vive en una tabla SQL Server compartida
(ver servicios/usados_db.py), que no tiene ese problema porque cada
inserción es atómica.

Usado por presentacion/cli.py (el .bat local).
"""

from pathlib import Path

from datos import app_config
from servicios import drive_storage


def load_drive_service_from_config():
    """Conecta con Drive usando las credenciales de .config/config.json (ver
    app_config.py). Devuelve (None, None) si no están configuradas o si la
    conexión falla, para que quien llame siga funcionando en modo
    local-only."""
    cfg = app_config.get_gdrive_config()
    if not cfg:
        return None, None
    try:
        service = drive_storage.get_service(cfg["client_id"], cfg["client_secret"], cfg["refresh_token"])
        return service, cfg["folder_id"]
    except Exception as exc:
        print(f"[!] No se pudo conectar con Google Drive, se sigue en modo local: {exc}")
        return None, None


def push_results_to_drive(service, folder_id: str, out_path: Path, caption_path: Path | None) -> None:
    drive_storage.upload_file(service, folder_id, out_path.name, out_path.read_bytes(), "video/mp4")
    if caption_path and caption_path.exists():
        drive_storage.upload_file(service, folder_id, caption_path.name, caption_path.read_bytes(), "text/plain")
