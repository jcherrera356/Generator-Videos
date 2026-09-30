"""
App de Streamlit: un botón que genera un video nuevo (usando el mismo
pipeline de generate_video.py) y lo guarda en una carpeta de Google Drive
— junto con el registro de "no repetir" — para que sobrevivan aunque esta
app se reinicie en la nube.

Configuración necesaria en Streamlit Cloud → Settings → Secrets:

    [gdrive]
    folder_id = "1EXJMY_OpD7rXxePU7YUqua75eWmSKeag"
    service_account = '''
    { ... contenido completo del JSON de la cuenta de servicio ... }
    '''

    [pexels]
    api_key = "..."

    [groq]
    api_key = "..."

Ver README.md para la guía paso a paso de cómo crear la cuenta de servicio
de Google y compartir la carpeta de Drive con ella.
"""

import json
from pathlib import Path

import streamlit as st

import drive_storage
import generate_video
import wikipedia_facts

BASE_DIR = Path(__file__).resolve().parent

STATE_FILES = [generate_video.USED_FILE, wikipedia_facts.USED_WIKI_FILE]


def _write_local_secrets() -> None:
    """Vuelca los secrets de Streamlit a los archivos config.json que ya
    usan pexels_photos.py y groq_client.py, sin tocar esos módulos."""
    if "pexels" in st.secrets:
        (BASE_DIR / "config.json").write_text(
            json.dumps({"pexels_api_key": st.secrets["pexels"]["api_key"]}), encoding="utf-8"
        )
    if "groq" in st.secrets:
        (BASE_DIR / "groq_config.json").write_text(
            json.dumps({"groq_api_key": st.secrets["groq"]["api_key"]}), encoding="utf-8"
        )


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


st.set_page_config(page_title="Generador de datos curiosos", page_icon="🎬")
st.title("🎬 Generador de videos de datos curiosos")
st.caption(
    "Cada clic genera un video vertical listo para TikTok (voz IA, fotos reales, "
    "personaje animado y subtítulos) y lo guarda en tu carpeta de Google Drive."
)

if "gdrive" not in st.secrets:
    st.error(
        "Falta configurar los secrets de Google Drive (`[gdrive]` con `folder_id` y "
        "`service_account`). Ver README.md, sección 'Desplegar en Streamlit Cloud'."
    )
    st.stop()

_write_local_secrets()
FOLDER_ID = st.secrets["gdrive"]["folder_id"]
SERVICE_ACCOUNT_INFO = json.loads(st.secrets["gdrive"]["service_account"])

if st.button("🎲 Generar video nuevo", type="primary"):
    try:
        service = drive_storage.get_service(SERVICE_ACCOUNT_INFO)

        with st.status("Generando video...", expanded=True) as status:
            st.write("Sincronizando registro de datos ya usados desde Drive...")
            _sync_state_from_drive(service, FOLDER_ID)

            st.write("Eligiendo dato, generando voz, fotos y personaje animado (1-3 min)...")
            out_path = generate_video.main()
            caption_path = out_path.with_suffix(".txt")

            st.write("Subiendo el video y el registro actualizado a Google Drive...")
            _push_state_and_video_to_drive(service, FOLDER_ID, out_path, caption_path)

            status.update(label="¡Listo! Video guardado en Drive.", state="complete")

        st.video(str(out_path))
        st.download_button(
            "⬇️ Descargar video",
            data=out_path.read_bytes(),
            file_name=out_path.name,
            mime="video/mp4",
        )
        if caption_path.exists():
            st.text_area("Título y hashtags sugeridos", caption_path.read_text(encoding="utf-8"), height=120)

    except Exception as exc:
        st.error(f"Ocurrió un error generando el video: {exc}")
        raise
