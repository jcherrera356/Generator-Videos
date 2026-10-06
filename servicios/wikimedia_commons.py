"""
Busca fotos reales en Wikimedia Commons (el banco de imágenes de Wikipedia)
para ilustrar un dato curioso — API pública, sin key, sin registro.

A diferencia de Pexels (fotos de stock genéricas, piensa "banco", "perro",
"ciudad"), Commons SÍ tiene fotos reales de personas, lugares y eventos
específicos (ej. una persona en particular, un equipo, un edificio puntual),
porque son las mismas fotos que ilustran los artículos de Wikipedia. Por eso
es la fuente PRINCIPAL de fotos del pipeline; Pexels queda como respaldo
para temas genéricos donde Commons no tenga nada bueno (pexels_photos.py).

Requisito de licencia: las fotos de Commons son de uso libre pero casi
todas piden atribución (CC-BY-SA la más común). Por eso generate_caption()
en generador_pipeline.py agrega una línea de atribución genérica al .txt
cuando las fotos vienen de aquí (mismo criterio que ya se usa para RAWG).
"""

from io import BytesIO

import requests
from PIL import Image

USER_AGENT = "ChicoTuf-GeneradorVideos/1.0 (uso personal)"
API_URL = "https://commons.wikimedia.org/w/api.php"
MIN_WIDTH = 400
ALLOWED_MIME = {"image/jpeg", "image/png"}


def _search_titles(keyword: str, limit: int) -> list[str]:
    try:
        r = requests.get(
            API_URL,
            params={
                "action": "query",
                "list": "search",
                "srsearch": f"{keyword} filetype:bitmap",
                "srnamespace": 6,  # namespace "File:"
                "srlimit": limit,
                "format": "json",
            },
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        r.raise_for_status()
        return [item["title"] for item in r.json().get("query", {}).get("search", [])]
    except (requests.RequestException, KeyError):
        return []


def _fetch_image_infos(titles: list[str]) -> list[dict]:
    if not titles:
        return []
    try:
        r = requests.get(
            API_URL,
            params={
                "action": "query",
                "titles": "|".join(titles),
                "prop": "imageinfo",
                "iiprop": "url|size|mime",
                "iiurlwidth": 1280,
                "format": "json",
            },
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        r.raise_for_status()
        pages = r.json().get("query", {}).get("pages", {})
        return [p["imageinfo"][0] for p in pages.values() if p.get("imageinfo")]
    except (requests.RequestException, KeyError, IndexError):
        return []


def _download_image(url: str) -> Image.Image | None:
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
        r.raise_for_status()
        return Image.open(BytesIO(r.content)).convert("RGB")
    except (requests.RequestException, OSError):
        return None


def fetch_topic_photos(keyword: str, count: int) -> list[Image.Image]:
    """Devuelve hasta `count` fotos reales de Commons relacionadas al tema,
    descartando logos/íconos (SVG, imágenes muy chicas). Lista vacía si no
    encuentra nada razonable (el pipeline cae a Pexels en ese caso)."""
    titles = _search_titles(keyword, limit=count * 3)
    infos = _fetch_image_infos(titles)

    photos: list[Image.Image] = []
    for info in infos:
        if len(photos) >= count:
            break
        if info.get("mime") not in ALLOWED_MIME:
            continue
        if info.get("width", 0) < MIN_WIDTH:
            continue
        url = info.get("thumburl") or info.get("url")
        if not url:
            continue
        img = _download_image(url)
        if img:
            photos.append(img)
    return photos
