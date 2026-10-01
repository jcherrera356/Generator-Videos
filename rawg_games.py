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

import groq_client

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "rawg_config.json"
USED_FILE = BASE_DIR / "used_games.json"
API_BASE = "https://api.rawg.io/api"
WIKI_USER_AGENT = "ChicoTuf-GeneradorVideos/1.0 (uso personal)"
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


def _fetch_wikipedia_extract(name: str) -> str | None:
    """Busca el juego en Wikipedia (primero en español, luego en inglés como
    respaldo) y devuelve el extracto del resumen, o None si no encuentra nada
    razonable. Se usa solo como contexto extra para la IA, no se muestra tal
    cual (puede venir en inglés)."""
    for lang, hint in (("es", "videojuego"), ("en", "video game")):
        try:
            search = requests.get(
                f"https://{lang}.wikipedia.org/w/api.php",
                params={"action": "opensearch", "search": f"{name} {hint}", "limit": 1, "format": "json"},
                headers={"User-Agent": WIKI_USER_AGENT},
                timeout=10,
            )
            search.raise_for_status()
            titles = search.json()[1]
            if not titles:
                continue
            title = titles[0].replace(" ", "_")
            summary = requests.get(
                f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}",
                headers={"User-Agent": WIKI_USER_AGENT},
                timeout=10,
            )
            summary.raise_for_status()
            extract = (summary.json().get("extract") or "").strip()
            if extract and len(extract) > 80:
                return extract
        except requests.RequestException:
            continue
    return None


def _build_curious_text(
    name: str,
    year: str,
    genres: list[str],
    platforms: list[str],
    developers: list[str],
    rating: float | None,
    metacritic: int | None,
    description_en: str,
    wiki_extract: str | None,
) -> str | None:
    """Usa Groq para traducir y sintetizar toda la info (en inglés y/o
    español) en un dato curioso natural, en vez de pegar texto en inglés sin
    traducir o repetir siempre la misma plantilla de estadísticas."""
    context_lines = [f"Juego: {name}"]
    if year:
        context_lines.append(f"Año de lanzamiento: {year}")
    if genres:
        context_lines.append(f"Género(s): {', '.join(genres)}")
    if developers:
        context_lines.append(f"Desarrollador(es): {', '.join(developers)}")
    if platforms:
        context_lines.append(f"Plataformas: {', '.join(platforms)}")
    if rating:
        context_lines.append(f"Calificación de los jugadores: {rating}/5")
    if metacritic:
        context_lines.append(f"Metascore: {metacritic}")
    if description_en:
        context_lines.append(f"Descripción (en inglés, de RAWG): {description_en}")
    if wiki_extract:
        context_lines.append(f"Extracto de Wikipedia: {wiki_extract}")

    system_prompt = (
        "Eres un redactor de 'datos curiosos' sobre videojuegos para TikTok, en "
        "español neutro. Te paso información en inglés y/o español sobre un "
        "juego; tu trabajo es traducir y resumir en 2 a 4 oraciones naturales y "
        "curiosas (nunca una ficha técnica ni una lista). Prioriza curiosidades "
        "reales si aparecen en la información: historia de desarrollo, récords, "
        "polémicas, easter eggs, cifras de ventas o impacto cultural. Varía la "
        "redacción y el inicio de cada respuesta, no uses siempre la misma "
        "estructura. No inventes datos que no estén en la información dada. "
        "Responde SOLO con el texto final en español, sin comillas, sin "
        "encabezados ni explicaciones."
    )
    return groq_client.chat(system_prompt, "\n".join(context_lines), max_tokens=220)


def _fallback_text(
    name: str,
    year: str,
    genres: list[str],
    platforms: list[str],
    developers: list[str],
    rating: float | None,
    metacritic: int | None,
) -> str:
    """Respaldo sin IA (si Groq no está configurado o falla): menos rico que
    la versión con IA, pero varía según qué datos haya disponibles en vez de
    repetir siempre la misma plantilla."""
    pieces = [f'"{name}"']
    details = []
    if genres:
        details.append(f"un juego de {', '.join(g.lower() for g in genres)}")
    if year:
        details.append(f"lanzado en {year}")
    if developers:
        details.append(f"desarrollado por {', '.join(developers)}")
    pieces.append(" es " + ", ".join(details) + "." if details else ".")
    if rating:
        pieces.append(f" Los jugadores lo califican con {rating}/5.")
    if metacritic:
        pieces.append(f" Tiene un Metascore de {metacritic}.")
    if platforms:
        pieces.append(f" Está disponible en {', '.join(platforms)}.")
    return "".join(pieces)


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

        description_en = (detail.get("description_raw") or "").replace("\n", " ").strip()[:1200]
        name = game.get("name", "este juego")
        year = (game.get("released") or "")[:4]
        rating = game.get("rating")
        metacritic = game.get("metacritic")
        genres = [g["name"] for g in detail.get("genres") or game.get("genres") or []]
        developers = [d["name"] for d in detail.get("developers") or []]
        platforms = [p["platform"]["name"] for p in detail.get("platforms") or game.get("platforms") or []]

        wiki_extract = _fetch_wikipedia_extract(name)
        full_text = _build_curious_text(
            name, year, genres, platforms, developers, rating, metacritic, description_en, wiki_extract
        )
        if not full_text:
            full_text = _fallback_text(name, year, genres, platforms, developers, rating, metacritic)

        full_text = full_text.strip()
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
