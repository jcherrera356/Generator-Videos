"""
Busca fotos reales relacionadas a un dato curioso usando la API gratuita de
Pexels: una serie de fotos (una por segmento del relato) para que la imagen
vaya cambiando a medida que el avatar habla, más una versión de fondo.

Requiere una API key gratuita (sin tarjeta de crédito) de https://www.pexels.com/api/
guardada en config.json como {"pexels_api_key": "..."}.
Si no hay key, no hay internet, o la búsqueda no da resultados, las funciones
devuelven listas vacías / None para que el script principal use el ícono
ilustrado como respaldo.
"""

import json
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageOps

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"


def _get_api_key() -> str | None:
    if not CONFIG_FILE.exists():
        return None
    try:
        config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    key = config.get("pexels_api_key", "").strip()
    return key or None


def fetch_topic_photos(keyword: str, count: int) -> list[Image.Image]:
    """Devuelve hasta `count` fotos reales distintas (RGB, sin recortar)."""
    api_key = _get_api_key()
    if not api_key:
        return []

    try:
        response = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": api_key},
            params={"query": keyword, "per_page": max(count, 3)},
            timeout=10,
        )
        response.raise_for_status()
        results = response.json().get("photos", [])
    except (requests.RequestException, KeyError):
        return []

    photos: list[Image.Image] = []
    for item in results[:count]:
        try:
            img_response = requests.get(item["src"]["large"], timeout=15)
            img_response.raise_for_status()
            photos.append(Image.open(BytesIO(img_response.content)).convert("RGB"))
        except (requests.RequestException, KeyError, OSError):
            continue
    return photos


def to_square_card(photo: Image.Image, size: int, radius: int) -> Image.Image:
    """Recorta una foto a cuadrado y le aplica esquinas redondeadas (RGBA)."""
    square = ImageOps.fit(photo, (size, size), method=Image.LANCZOS)
    rgba = square.convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    rgba.putalpha(mask)
    return rgba


def to_cover_rgb(photo: Image.Image, width: int, height: int) -> Image.Image:
    """Recorta/escala una foto para cubrir por completo un lienzo width x height."""
    return ImageOps.fit(photo, (width, height), method=Image.LANCZOS)
