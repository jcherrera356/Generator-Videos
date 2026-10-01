"""
App de Streamlit: tres botones que generan un video nuevo (usando el mismo
pipeline de generate_video.py) — Wikipedia, el banco local (facts_bank.json)
o videojuegos (API de RAWG) — y lo guardan en una carpeta de Google Drive,
junto con el registro de "no repetir", para que sobrevivan aunque esta app
se reinicie en la nube.

Configuración necesaria en Streamlit Cloud → Settings → Secrets:

    [gdrive]
    folder_id = "1EXJMY_OpD7rXxePU7YUqua75eWmSKeag"
    client_id = "..."
    client_secret = "..."
    refresh_token = "..."

    [pexels]
    api_key = "..."

    [groq]
    api_key = "..."

    [rawg]
    api_key = "..."

Los 3 valores de [gdrive] (además de folder_id) salen de correr
google_drive_auth.py una sola vez en tu PC. Ver README.md para la guía
paso a paso.
"""

from pathlib import Path

import streamlit as st

import app_config
import drive_storage
import generate_video
import rawg_games
import wikipedia_facts

BASE_DIR = Path(__file__).resolve().parent

STATE_FILES = [generate_video.USED_FILE, wikipedia_facts.USED_WIKI_FILE, rawg_games.USED_FILE]


def _write_local_secrets() -> None:
    """Vuelca los secrets de Streamlit al único .config/config.json que usan
    pexels_photos.py, groq_client.py, rawg_games.py y generate_video.py
    (ver app_config.py), sin tocar esos módulos."""
    data = {}
    if "pexels" in st.secrets:
        data["pexels_api_key"] = st.secrets["pexels"]["api_key"]
    if "groq" in st.secrets:
        data["groq_api_key"] = st.secrets["groq"]["api_key"]
    if "rawg" in st.secrets:
        data["rawg_api_key"] = st.secrets["rawg"]["api_key"]
    if "gdrive" in st.secrets:
        data["gdrive"] = dict(st.secrets["gdrive"])
    app_config.save(data)


def _sync_state_from_drive(service, folder_id: str) -> None:
    for path in STATE_FILES:
        data = drive_storage.download_file(service, folder_id, path.name)
        if data:
            path.write_bytes(data)


def _push_state_and_video_to_drive(service, folder_id: str, video_path: Path, caption_path: Path | None) -> None:
    drive_storage.upload_file(service, folder_id, video_path.name, video_path.read_bytes(), "video/mp4")
    if caption_path and caption_path.exists():
        drive_storage.upload_file(service, folder_id, caption_path.name, caption_path.read_bytes(), "text/plain")
    for path in STATE_FILES:
        if path.exists():
            drive_storage.upload_file(service, folder_id, path.name, path.read_bytes(), "application/json")


st.set_page_config(page_title="Generador de datos curiosos")
st.title("Generador de videos de datos curiosos")
st.caption(
    "Cada clic genera un video vertical listo para TikTok (voz IA, fotos reales, "
    "personaje animado y subtítulos) y lo guarda en tu carpeta de Google Drive."
)

if "gdrive" not in st.secrets:
    st.error(
        "Falta configurar los secrets de Google Drive (`[gdrive]` con `folder_id`, "
        "`client_id`, `client_secret` y `refresh_token`). Ver README.md, sección "
        "'Desplegar en Streamlit Cloud'."
    )
    st.stop()

_write_local_secrets()
FOLDER_ID = st.secrets["gdrive"]["folder_id"]


def _generate_and_upload(source: str) -> None:
    try:
        service = drive_storage.get_service(
            st.secrets["gdrive"]["client_id"],
            st.secrets["gdrive"]["client_secret"],
            st.secrets["gdrive"]["refresh_token"],
        )

        with st.status("Generando video...", expanded=True) as status:
            st.write("Sincronizando registro de datos ya usados desde Drive...")
            _sync_state_from_drive(service, FOLDER_ID)

            st.write("Eligiendo dato, generando voz, fotos y personaje animado (1-3 min)...")
            out_path = generate_video.main(source=source)
            caption_path = out_path.with_suffix(".txt")

            st.write("Subiendo el video y el registro actualizado a Google Drive...")
            _push_state_and_video_to_drive(service, FOLDER_ID, out_path, caption_path)

            status.update(label="¡Listo! Video guardado en Drive.", state="complete")

        st.video(str(out_path))
        st.download_button(
            "Descargar video",
            data=out_path.read_bytes(),
            file_name=out_path.name,
            mime="video/mp4",
        )
        if caption_path.exists():
            st.text_area("Título y hashtags sugeridos", caption_path.read_text(encoding="utf-8"), height=120)

    except Exception as exc:
        st.error(f"Ocurrió un error generando el video: {exc}")
        raise


col1, col2, col3 = st.columns(3)
with col1:
    st.subheader("Desde Wikipedia")
    st.caption("Un dato al azar, recién traído de Wikipedia (sin repetir).")
    wiki_clicked = st.button("Generar con Wikipedia", type="primary", use_container_width=True)
with col2:
    st.subheader("Desde el banco local")
    st.caption("Un dato elegido del banco fijo facts_bank.json (sin repetir).")
    local_clicked = st.button("Generar con banco local", type="secondary", use_container_width=True)
with col3:
    st.subheader("Videojuegos")
    st.caption("Un juego al azar con sus propias capturas reales (API de RAWG, sin repetir).")
    games_clicked = st.button("Generar sobre videojuegos", type="secondary", use_container_width=True)

if wiki_clicked:
    _generate_and_upload(source="wikipedia")
elif local_clicked:
    _generate_and_upload(source="local")
elif games_clicked:
    _generate_and_upload(source="games")
