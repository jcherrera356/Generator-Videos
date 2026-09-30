"""
Cliente mínimo para la API de Groq (LLM gratuito en la nube), usado para
darle personalidad al avatar: chistes, saludos y respuestas al chat.

Requiere una API key gratuita de https://console.groq.com/keys guardada en
groq_config.json como {"groq_api_key": "..."}. Si falta la key o algo falla
(sin internet, límite de uso, etc.), `chat()` devuelve None para que quien
la llame pueda usar un texto de respaldo sin romper el directo.
"""

import json
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "groq_config.json"

# Catálogo de Groq cambia con el tiempo; si este modelo deja de existir,
# revisa los disponibles en https://console.groq.com/docs/models
MODEL = "openai/gpt-oss-20b"


def _get_api_key() -> str | None:
    if not CONFIG_FILE.exists():
        return None
    try:
        config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    key = config.get("groq_api_key", "").strip()
    return key or None


def chat(system_prompt: str, user_message: str, max_tokens: int = 120) -> str | None:
    api_key = _get_api_key()
    if not api_key:
        return None
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": max_tokens,
                "reasoning_effort": "low",
                "temperature": 0.9,
            },
            timeout=10,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
        return content or None
    except (requests.RequestException, KeyError, IndexError):
        return None
