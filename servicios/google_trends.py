"""
Trae temas en tendencia en Google ahora mismo (últimas 24 horas) vía el RSS
público de Google Trends (https://trends.google.com/trending/rss) — sin API
key, sin librería extra (pytrends dejó de funcionar: Google movió sus
endpoints internos de "trending searches", este RSS es el reemplazo que
Google expone en su rediseño de Google Trends). Se usa para generar datos
curiosos sobre lo que la gente está buscando en este momento, en vez de un
tema al azar.

Si el RSS falla (Google lo vuelve a mover, sin internet, etc.),
fetch_unused_trend() devuelve None para que el script principal use el
banco local como respaldo — el video nunca falla por esto.
"""

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

from servicios import groq_client

BASE_DIR = Path(__file__).resolve().parent.parent
USED_FILE = BASE_DIR / "used_trends.json"
MAX_TRACKED = 500

RSS_URL = "https://trends.google.com/trending/rss"
HT_NS = "https://trends.google.com/trending/rss"
# "GLOBAL" es una categoria real del RSS (se confirmo probandola -- devuelve
# una lista mas corta y genuinamente mundial, en varios idiomas, distinta a
# la de cualquier pais puntual). Antes estaba en "CO" (Colombia), pero salian
# temas demasiado locales/especificos. Usa un codigo de pais (ej. "CO", "US",
# "MX") en vez de "GLOBAL" si prefieres tendencias de un mercado puntual.
COUNTRY = "GLOBAL"

# Google no deja filtrar el RSS por categoría (se probó con varios nombres
# de parámetro, los ignora todos en silencio) -- en vez de eso, se le pide a
# la IA que clasifique cada tema dentro de esta lista al mismo tiempo que
# redacta el dato, y se descartan los temas que no coincidan con la
# categoría pedida.
CATEGORIES = [
    "Videojuegos", "Noticias", "Moda", "Entretenimiento", "Tecnología",
    "Deportes", "Negocios", "Salud", "Ciencia", "Otros",
]


def _load_used() -> list[str]:
    if USED_FILE.exists():
        return json.loads(USED_FILE.read_text(encoding="utf-8"))
    return []


def _save_used(used: list[str]) -> None:
    USED_FILE.write_text(json.dumps(used[-MAX_TRACKED:], ensure_ascii=False, indent=2), encoding="utf-8")


def _fetch_trending_items() -> list[dict]:
    """Devuelve [{"term": ..., "news": [titulo, ...]}] de las últimas 24h."""
    try:
        r = requests.get(
            RSS_URL,
            params={"geo": COUNTRY, "hours": 24},
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except (requests.RequestException, ET.ParseError):
        return []

    items = []
    for item in root.findall(".//item"):
        title_el = item.find("title")
        if title_el is None or not title_el.text:
            continue
        news_titles = [
            n.text
            for n in item.findall(f"{{{HT_NS}}}news_item/{{{HT_NS}}}news_item_title")
            if n is not None and n.text
        ]
        items.append({"term": title_el.text.strip(), "news": news_titles[:3]})
    return items


def _build_curious_text(term: str, news_titles: list[str]) -> tuple[str, str, str] | None:
    """Devuelve (categoria, texto, palabras_clave) o None si la IA decide
    que no hay suficiente información confiable para explicar el tema."""
    context = f"Tema en tendencia ahora en buscadores: {term}"
    if news_titles:
        context += "\nTitulares de noticias relacionadas:\n" + "\n".join(f"- {t}" for t in news_titles)

    system_prompt = (
        "Eres un redactor de 'datos curiosos' para TikTok, en español neutro. "
        "Te doy un tema en tendencia ahora mismo (la fuente es un RSS mundial, "
        "puede venir en cualquier idioma) junto con titulares de noticias "
        "relacionadas. LEE BIEN esa información antes de escribir.\n\n"
        "Responde EXACTAMENTE en este formato, sin nada más:\n"
        f"CATEGORIA: <una de estas, la que mejor encaje: {', '.join(CATEGORIES)}>\n"
        "PALABRAS_CLAVE: <2-4 palabras EN INGLES que describan el sujeto "
        "visual principal (ej. nombre de la persona/equipo/lugar/cosa), para "
        "buscar fotos reales>\n"
        "TEXTO: <el dato curioso, en español>\n\n"
        "Para TEXTO: traduce al español si el tema/titulares vienen en otro "
        "idioma, y explica con precisión de qué se trata el tema y por qué es "
        "relevante ahora, en 2 o 3 oraciones naturales y bien desarrolladas (no "
        "un resumen apurado ni un titular copiado ni tu opinión) — el video dura "
        "entre 15 y 30 segundos narrado, así que apunta a unos 300-400 "
        "caracteres en total. Si el tema es demasiado ambiguo (ej. un nombre "
        "propio sin contexto suficiente en los titulares) o no hay información "
        "confiable para explicarlo bien, responde exactamente con TEXTO: SKIP. "
        "No inventes datos que no estén en los titulares."
    )
    reply = groq_client.chat(system_prompt, context, max_tokens=260)
    if not reply:
        return None

    cat_match = re.search(r"CATEGOR[IÍ]A:\s*(.+)", reply, re.IGNORECASE)
    keywords_match = re.search(r"PALABRAS_CLAVE:\s*(.+)", reply, re.IGNORECASE)
    text_match = re.search(r"TEXTO:\s*(.+)", reply, re.IGNORECASE | re.DOTALL)
    if not text_match:
        return None

    text = text_match.group(1).strip()
    if not text or text.upper() == "SKIP" or len(text) < 60:
        return None

    category = cat_match.group(1).strip() if cat_match else "Otros"
    keywords = keywords_match.group(1).strip() if keywords_match else term
    return category, text, keywords


def fetch_unused_trend(max_attempts: int = 8, category: str | None = None) -> dict | None:
    """Devuelve un dato (mismo formato que facts_bank.json) sobre un tema en
    tendencia no usado antes. Si se pasa `category` (una de CATEGORIES),
    solo acepta temas que la IA clasifique en esa categoría -- prueba con
    varios temas de la lista hasta encontrar uno que encaje o agotar
    max_attempts. Sin fotos propias — el pipeline principal busca fotos en
    Wikimedia Commons/Pexels usando `keywords` (palabras en inglés que
    sugiere la IA, no el término crudo -- útil cuando el tema viene en un
    idioma que no da buenos resultados de búsqueda de imágenes)."""
    items = _fetch_trending_items()
    if not items:
        return None

    used = _load_used()
    # Si se pide una categoría puntual, revisa todos los temas disponibles
    # (ya se trajeron en un solo request, no cuesta nada extra en red) en vez
    # de limitarse a los primeros max_attempts -- una categoría como "Moda"
    # puede no estar entre los primeros temas del día.
    limit = len(items) if category else max_attempts
    for item in items[:limit]:
        term = item["term"]
        term_id = "trend-" + "".join(c if c.isalnum() else "-" for c in term.lower()).strip("-")[:60]
        if term_id in used:
            continue

        result = _build_curious_text(term, item["news"])
        if not result:
            continue
        item_category, text, keywords = result
        if category and item_category.strip().lower() != category.strip().lower():
            continue

        used.append(term_id)
        _save_used(used)
        return {
            "id": term_id,
            "category": "general",
            "keywords": keywords,
            "text": text,
        }
    return None
