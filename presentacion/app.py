"""
Capa de presentación: app de Streamlit con cuatro botones que generan un
video nuevo (usando el pipeline de aplicacion/generador_pipeline.py) —
Wikipedia, el banco local (facts_bank.json), videojuegos (API de RAWG) o
tendencias (Google Trends, con categoría opcional) — y lo guardan en una
carpeta de Google Drive (aplicacion/drive_sync.py), junto con el registro
de "no repetir", para que sobrevivan aunque esta app se reinicie en la
nube.

Config: lee directo de .config/config.json (ver datos/app_config.py) --
igual que el .bat local, sin pasar por Streamlit Secrets. Por eso este
archivo SÍ se sube a git a propósito (ver README, sección "Desplegar en
Streamlit Cloud") -- el repo debe ser privado para que esto sea seguro.

Nota: en el dashboard de Streamlit Cloud, el "Main file path" debe apuntar
a presentacion/app.py (no a app.py en la raíz, que ya no existe).
"""

import sys
from pathlib import Path

# Para poder importar "aplicacion", "servicios", etc. como paquetes de nivel
# superior sin importar desde dónde Streamlit ejecute este script, se agrega
# la raíz del proyecto al sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from aplicacion import drive_sync, generador_pipeline  # noqa: E402
from datos import app_config  # noqa: E402
from servicios import google_trends  # noqa: E402

st.set_page_config(page_title="Generador de datos curiosos")
st.title("Generador de videos de datos curiosos")
st.caption(
    "Cada clic genera un video vertical listo para TikTok (voz IA, fotos reales, "
    "personaje animado y subtítulos) y lo guarda en tu carpeta de Google Drive."
)

GDRIVE_CFG = app_config.get_gdrive_config()
if not GDRIVE_CFG:
    st.error(
        "Falta la sección \"gdrive\" en .config/config.json (folder_id, client_id, "
        "client_secret, refresh_token). Ver README.md, sección 'Desplegar en "
        "Streamlit Cloud'."
    )
    st.stop()

FOLDER_ID = GDRIVE_CFG["folder_id"]


def _generate_and_upload(source: str, trend_category: str | None = None) -> None:
    try:
        service, _ = drive_sync.load_drive_service_from_config()

        with st.status("Generando video...", expanded=True) as status:
            st.write("Sincronizando registro de datos ya usados desde Drive...")
            if service:
                drive_sync.sync_state_from_drive(service, FOLDER_ID)

            st.write("Eligiendo dato, generando voz, fotos y personaje animado (1-3 min)...")
            out_path = generador_pipeline.main(source=source, trend_category=trend_category)
            caption_path = out_path.with_suffix(".txt")

            st.write("Subiendo el video y el registro actualizado a Google Drive...")
            if service:
                drive_sync.push_results_to_drive(service, FOLDER_ID, out_path, caption_path)

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


col1, col2, col3, col4 = st.columns(4)
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
with col4:
    st.subheader("Tendencias")
    st.caption("Un tema en tendencia ahora en Google (últimas 24h, sin repetir).")
    trend_category_choice = st.selectbox(
        "Categoría", ["Cualquiera"] + google_trends.CATEGORIES, label_visibility="collapsed"
    )
    trending_clicked = st.button("Generar sobre tendencias", type="secondary", use_container_width=True)

if wiki_clicked:
    _generate_and_upload(source="wikipedia")
elif local_clicked:
    _generate_and_upload(source="local")
elif games_clicked:
    _generate_and_upload(source="games")
elif trending_clicked:
    category = None if trend_category_choice == "Cualquiera" else trend_category_choice
    _generate_and_upload(source="trending", trend_category=category)
