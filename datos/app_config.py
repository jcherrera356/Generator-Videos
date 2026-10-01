"""
Config central del proyecto: todas las API keys y credenciales (Pexels,
Groq, RAWG, Google Drive) viven en un solo archivo, `.config/config.json`,
en vez de repartidas en 4 archivos sueltos como antes (config.json,
groq_config.json, rawg_config.json, gdrive_config.json). No se sube a git
(ver .gitignore).

Formato esperado:
{
  "pexels_api_key": "...",
  "groq_api_key": "...",
  "rawg_api_key": "...",
  "gdrive": {
    "folder_id": "...",
    "client_id": "...",
    "client_secret": "...",
    "refresh_token": "..."
  }
}

Cualquier clave que falte hace que la función correspondiente devuelva None
— cada módulo que la usa (pexels_photos.py, groq_client.py, rawg_games.py,
generate_video.py) ya sabe seguir funcionando sin esa fuente en particular.
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / ".config"
CONFIG_FILE = CONFIG_DIR / "config.json"


def _load() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save(data: dict) -> None:
    CONFIG_DIR.mkdir(exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_pexels_api_key() -> str | None:
    return (_load().get("pexels_api_key") or "").strip() or None


def get_groq_api_key() -> str | None:
    return (_load().get("groq_api_key") or "").strip() or None


def get_rawg_api_key() -> str | None:
    return (_load().get("rawg_api_key") or "").strip() or None


def get_gdrive_config() -> dict | None:
    cfg = _load().get("gdrive") or {}
    required = ("folder_id", "client_id", "client_secret", "refresh_token")
    if not all(cfg.get(k) for k in required):
        return None
    return cfg
