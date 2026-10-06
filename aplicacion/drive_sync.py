"""
Capa de aplicación: sincroniza el video generado y el registro de "no
repetir" (used_facts.json, used_wikipedia.json, used_games.json,
used_trends.json) con una carpeta de Google Drive, para que ese registro
sobreviva entre corridas y en distintos equipos.

Usado por presentacion/cli.py (el .bat local).
"""

from pathlib import Path

from aplicacion import generador_pipeline
from datos import app_config
from servicios import drive_storage, google_trends, rawg_games, wikipedia_facts

STATE_FILES = [
    generador_pipeline.USED_FILE,
    wikipedia_facts.USED_WIKI_FILE,
    rawg_games.USED_FILE,
    google_trends.USED_FILE,
]


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


def sync_state_from_drive(service, folder_id: str) -> None:
    for path in STATE_FILES:
        data = drive_storage.download_file(service, folder_id, path.name)
        if data:
            path.write_bytes(data)


def push_results_to_drive(service, folder_id: str, out_path: Path, caption_path: Path | None) -> None:
    drive_storage.upload_file(service, folder_id, out_path.name, out_path.read_bytes(), "video/mp4")
    if caption_path and caption_path.exists():
        drive_storage.upload_file(service, folder_id, caption_path.name, caption_path.read_bytes(), "text/plain")
    for path in STATE_FILES:
        if path.exists():
            drive_storage.upload_file(service, folder_id, path.name, path.read_bytes(), "application/json")
