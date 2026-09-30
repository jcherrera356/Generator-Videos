"""
Trae datos curiosos en tiempo real desde la API pública de Wikipedia
(artículo aleatorio), como alternativa al banco fijo de facts_bank.json.
No requiere API key ni registro.

Lleva registro de los títulos ya usados (used_wikipedia.json) para no
repetir el mismo artículo en videos futuros.
"""

import json
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
USED_WIKI_FILE = BASE_DIR / "used_wikipedia.json"
USER_AGENT = "ChicoTuf-GeneradorVideos/1.0 (uso personal)"
MAX_TRACKED = 500


def _load_used() -> list[str]:
    if USED_WIKI_FILE.exists():
        return json.loads(USED_WIKI_FILE.read_text(encoding="utf-8"))
    return []


def _save_used(used: list[str]) -> None:
    USED_WIKI_FILE.write_text(json.dumps(used[-MAX_TRACKED:], ensure_ascii=False, indent=2), encoding="utf-8")


def _fetch_random_summary(lang: str = "es") -> tuple[str, str] | None:
    try:
        r = requests.get(
            f"https://{lang}.wikipedia.org/api/rest_v1/page/random/summary",
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        title = (data.get("title") or "").strip()
        extract = (data.get("extract") or "").strip()
        # Filtra artículos "stub" muy cortos (poco interesantes para un video)
        if not title or not extract or len(extract) < 150:
            return None
        return title, extract
    except requests.RequestException:
        return None


def _slugify(title: str) -> str:
    slug = "".join(c if c.isalnum() else "-" for c in title.lower().strip())
    while "--" in slug:
        slug = slug.replace("--", "-")
    return f"wiki-{slug.strip('-')[:60]}"


def fetch_unused_fact(max_attempts: int = 10) -> dict | None:
    """Devuelve un dato en el mismo formato que facts_bank.json, tomado de
    un artículo de Wikipedia que no se haya usado antes. Devuelve None si
    falla (sin internet, etc.) para que el script principal use el banco
    local como respaldo.
    """
    used = _load_used()
    for _ in range(max_attempts):
        result = _fetch_random_summary()
        if not result:
            continue
        title, extract = result
        fact_id = _slugify(title)
        if fact_id in used:
            continue

        sentences = extract.replace("\n", " ").split(". ")
        text = ". ".join(sentences[:3]).strip()
        if not text.endswith("."):
            text += "."

        used.append(fact_id)
        _save_used(used)
        return {"id": fact_id, "category": "general", "keywords": title, "text": text}
    return None
