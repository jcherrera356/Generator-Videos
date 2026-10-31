"""
Busca fotos reales relacionadas a un dato curioso usando la API gratuita de
Pixabay. Es la fuente PRINCIPAL de fotos del pipeline (ver
aplicacion/generador_pipeline.py); Wikimedia Commons y Pexels completan lo
que falte cuando Pixabay no encuentra suficientes fotos buenas.

Requiere una API key gratuita (sin tarjeta de crédito) de
https://pixabay.com/api/docs/ guardada en .config/config.json (ver
app_config.py) como {"pixabay_api_key": "..."}.
Si no hay key, no hay internet, o la búsqueda no da resultados, devuelve
una lista vacía para que el pipeline siga con el siguiente respaldo.
"""

from io import BytesIO

import requests
from PIL import Image

from datos import app_config

API_URL = "https://pixabay.com/api/"


def _is_relevant(tags: str, keyword: str) -> bool:
    """Pixabay empareja de forma laxa (una sola palabra en común ya cuenta
    como resultado, ej. "deadpool cosplay" trae fotos etiquetadas solo
    "cosplay" sin relación real). Para no aceptar esos falsos positivos, se
    exige que TODAS las palabras significativas de `keyword` (más de 2
    letras) aparezcan en las etiquetas de la foto."""
    words = [w.lower() for w in keyword.split() if len(w) > 2]
    if not words:
        return True
    tags_lower = tags.lower()
    return all(w in tags_lower for w in words)


def fetch_topic_photos(keyword: str, count: int) -> list[Image.Image]:
    """Devuelve hasta `count` fotos reales distintas (RGB, sin recortar),
    descartando resultados cuyas etiquetas no coincidan de verdad con la
    búsqueda."""
    api_key = app_config.get_pixabay_api_key()
    if not api_key:
        return []

    try:
        response = requests.get(
            API_URL,
            params={
                "key": api_key,
                "q": keyword,
                "image_type": "photo",
                "safesearch": "true",
                "per_page": max(count * 3, 10),
            },
            timeout=10,
        )
        response.raise_for_status()
        results = response.json().get("hits", [])
    except (requests.RequestException, KeyError, ValueError):
        return []

    photos: list[Image.Image] = []
    for item in results:
        if len(photos) >= count:
            break
        if not _is_relevant(item.get("tags", ""), keyword):
            continue
        try:
            img_response = requests.get(item["largeImageURL"], timeout=15)
            img_response.raise_for_status()
            photos.append(Image.open(BytesIO(img_response.content)).convert("RGB"))
        except (requests.RequestException, KeyError, OSError):
            continue
    return photos
