"""
Trae datos curiosos en tiempo real desde la API pública de Wikipedia
(artículo aleatorio), como alternativa al banco fijo de facts_bank.json.
No requiere API key ni registro.

El resumen crudo de Wikipedia se reescribe con IA (Groq) para dar más
contexto y mejor explicación que un simple recorte de las primeras
oraciones; si Groq no está disponible, cae al recorte de siempre.

Lleva registro de los títulos ya usados (used_wikipedia.json) para no
repetir el mismo artículo en videos futuros.
"""

import requests

from servicios import groq_client, usados_db

USER_AGENT = "ChicoTuf-GeneradorVideos/1.0 (uso personal)"


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


def _build_curious_text(title: str, extract: str) -> str | None:
    system_prompt = (
        "Eres un redactor de 'datos curiosos' para TikTok, en español neutro. "
        "Te doy el resumen de un artículo de Wikipedia. LEE BIEN el resumen "
        "antes de escribir — tu trabajo es explicar de qué se trata con "
        "contexto, mejor que un simple recorte, resaltando lo más curioso o "
        "relevante, en 2 o 3 oraciones naturales y bien desarrolladas (no "
        "copies el resumen tal cual ni des tu opinión) — el video dura entre "
        "15 y 30 segundos narrado, así que apunta a unos 300-400 caracteres "
        "en total. No inventes datos que no estén en el resumen. Responde "
        "solo con el texto final en español, sin comillas ni explicaciones."
    )
    user_prompt = f"Tema: {title}\nResumen de Wikipedia: {extract}"
    reply = groq_client.chat(system_prompt, user_prompt, max_tokens=260)
    if not reply:
        return None
    text = reply.strip()
    return text if len(text) >= 60 else None


def _fallback_text(extract: str) -> str:
    """Si Groq no está disponible: recorta el extracto a las primeras 3
    oraciones, como antes."""
    sentences = extract.replace("\n", " ").split(". ")
    text = ". ".join(sentences[:3]).strip()
    if not text.endswith("."):
        text += "."
    return text


def fetch_unused_fact(max_attempts: int = 10) -> dict | None:
    """Devuelve un dato en el mismo formato que facts_bank.json, tomado de
    un artículo de Wikipedia que no se haya usado antes, con el texto
    reescrito por IA para dar más contexto. Devuelve None si falla (sin
    internet, etc.) para que el script principal use el banco local como
    respaldo.
    """
    used = usados_db.get_used_set("wikipedia")
    for _ in range(max_attempts):
        result = _fetch_random_summary()
        if not result:
            continue
        title, extract = result
        fact_id = _slugify(title)
        if fact_id in used:
            continue

        text = _build_curious_text(title, extract) or _fallback_text(extract)

        usados_db.mark_used("wikipedia", fact_id)
        return {"id": fact_id, "category": "general", "keywords": title, "text": text}
    return None
