"""
Trae datos curiosos sobre videojuegos desde la API de RAWG (rawg.io), con
sus propias imágenes reales (capturas/arte del juego) en vez de fotos
genéricas de Pexels — así el video queda con imágenes del juego real.

Requiere una API key gratuita de https://rawg.io/apidocs (hasta 20,000
solicitudes/mes gratis para uso no comercial). Guárdala en rawg_config.json:
    {"rawg_api_key": "..."}

Nota de atribución: los términos del plan gratuito de RAWG piden mencionar
"RAWG" como fuente, con un link activo donde se use su data/imágenes. Por
eso generate_caption() en generate_video.py agrega esa mención cuando el
dato viene de aquí. Si tu canal supera 100,000 usuarios activos/mes o
500,000 vistas de página al mes, sus términos piden contactarlos para un
licenciamiento distinto.

Si no hay API key, sin internet, o RAWG no responde, fetch_unused_game()
devuelve None para que el script principal use el banco local como
respaldo — el video nunca falla por esto.
"""

import json
import random
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "rawg_config.json"
USED_FILE = BASE_DIR / "used_games.json"
API_BASE = "https://api.rawg.io/api"
MAX_TRACKED = 500


def _get_api_key() -> str | None:
    if not CONFIG_FILE.exists():
        return None
    try:
        config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    key = config.get("rawg_api_key", "").strip()
    return key or None


def _load_used() -> list[str]:
    if USED_FILE.exists():
        return json.loads(USED_FILE.read_text(encoding="utf-8"))
    return []


def _save_used(used: list[str]) -> None:
    USED_FILE.write_text(json.dumps(used[-MAX_TRACKED:], ensure_ascii=False, indent=2), encoding="utf-8")


def _download_image(url: str) -> Image.Image | None:
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return Image.open(BytesIO(r.content)).convert("RGB")
    except (requests.RequestException, OSError):
        return None


def _fetch_screenshots(api_key: str, game_id: int, fallback_image: str | None, limit: int = 4) -> list[Image.Image]:
    images: list[Image.Image] = []
    try:
        r = requests.get(f"{API_BASE}/games/{game_id}/screenshots", params={"key": api_key}, timeout=10)
        r.raise_for_status()
        for shot in r.json().get("results", [])[:limit]:
            img = _download_image(shot["image"])
            if img:
                images.append(img)
    except requests.RequestException:
        pass

    if not images and fallback_image:
        img = _download_image(fallback_image)
        if img:
            images.append(img)
    return images


def fetch_unused_game(max_attempts: int = 8) -> dict | None:
    """Devuelve un dato (mismo formato que facts_bank.json, más una lista
    de fotos reales ya descargadas) sobre un videojuego no usado antes."""
    api_key = _get_api_key()
    if not api_key:
        return None

    used = _load_used()
    for _ in range(max_attempts):
        page = random.randint(1, 15)
        try:
            response = requests.get(
                f"{API_BASE}/games",
                params={"key": api_key, "ordering": "-rating", "page_size": 20, "page": page},
                timeout=10,
            )
            response.raise_for_status()
            results = response.json().get("results", [])
        except requests.RequestException:
            return None

        candidates = [g for g in results if f"game-{g['id']}" not in used]
        if not candidates:
            continue
        game = random.choice(candidates)

        try:
            detail = requests.get(f"{API_BASE}/games/{game['id']}", params={"key": api_key}, timeout=10).json()
        except requests.RequestException:
            detail = {}

        description = (detail.get("description_raw") or "").replace("\n", " ").strip()
        text_desc = ". ".join(description.split(". ")[:3]).strip()
        if text_desc and not text_desc.endswith("."):
            text_desc += "."

        name = game.get("name", "este juego")
        year = (game.get("released") or "")[:4]
        rating = game.get("rating")
        metacritic = game.get("metacritic")

        intro = f'"{name}"' + (f" salió en {year}. " if year else ". ")
        if rating:
            intro += f"Tiene una calificación de {rating}/5 de los jugadores. "
        if metacritic:
            intro += f"Su Metascore es de {metacritic}. "

        full_text = (intro + text_desc).strip()
        if len(full_text) < 60:
            continue

        fact_id = f"game-{game['id']}"
        used.append(fact_id)
        _save_used(used)

        return {
            "id": fact_id,
            "category": "videojuegos",
            "keywords": name,
            "text": full_text[:600],
            "photos": _fetch_screenshots(api_key, game["id"], game.get("background_image")),
        }
    return None
