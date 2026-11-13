"""
Capa de presentación: app de Streamlit con cuatro botones que generan un
video nuevo (usando el pipeline de aplicacion/generador_pipeline.py) —
Wikipedia, el banco local (tabla SQL videosApp.FactsBank), videojuegos (API
de RAWG) o tendencias (Google Trends, con categoría opcional) — y lo
guardan en una carpeta de Google Drive (aplicacion/drive_sync.py).

El registro de "no repetir" y el banco de datos curiosos fijos viven en SQL
Server (ver servicios/sql_database.py, usados_db.py, facts_bank_db.py) —
por eso esta app, igual que el .bat local, depende de esa base de datos
para poder generar cualquier video; si no conecta, se corta con un error
claro en vez de generar un video sin poder registrarlo.

Configuración necesaria en Streamlit Cloud → Settings → Secrets:

    [sql_server]
    server = "..."
    database = "..."
    user = "..."
    password = "..."

    [pexels]
    api_key = "..."

    [groq]
    api_key = "..."

    [rawg]
    api_key = "..."

    [gdrive]
    folder_id = "1EXJMY_OpD7rXxePU7YUqua75eWmSKeag"
    client_id = "..."
    client_secret = "..."
    refresh_token = "..."

`[sql_server]` es la única sección obligatoria (sin ella la app no genera
ningún video). Las demás son opcionales: sin `[gdrive]` el video no se sube
a Drive (solo se puede descargar desde la propia app); sin pexels/groq/rawg
cada fuente externa cae a su respaldo normal.

IMPORTANTE: .config/config.json NUNCA se sube a git (ver .gitignore) --
tiene credenciales reales. En la nube se usan los Secrets de Streamlit en
su lugar, nunca el archivo.

Nota: en el dashboard de Streamlit Cloud, el "Main file path" debe apuntar
a presentacion/app.py.
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
from servicios import google_trends, sql_database  # noqa: E402


def _write_local_secrets() -> None:
    """Vuelca los secrets de Streamlit al único .config/config.json que usan
    los servicios (pexels_photos.py, groq_client.py, rawg_games.py,
    sql_database.py) y la subida a Drive (ver datos/app_config.py), sin
    tocar esos módulos. Este archivo solo existe en el disco temporal del
    contenedor de Streamlit Cloud -- nunca se sube a git."""
    data = {}
    if "pexels" in st.secrets:
        data["pexels_api_key"] = st.secrets["pexels"]["api_key"]
    if "pixabay" in st.secrets:
        data["pixabay_api_key"] = st.secrets["pixabay"]["api_key"]
    if "groq" in st.secrets:
        data["groq_api_key"] = st.secrets["groq"]["api_key"]
    if "rawg" in st.secrets:
        data["rawg_api_key"] = st.secrets["rawg"]["api_key"]
    if "sql_server" in st.secrets:
        data["sql_server"] = dict(st.secrets["sql_server"])
    if "gdrive" in st.secrets:
        data["gdrive"] = dict(st.secrets["gdrive"])
    app_config.save(data)


st.set_page_config(page_title="Generador de datos curiosos")
st.title("Generador de videos de datos curiosos")
st.caption(
    "Cada clic genera un video vertical listo para TikTok (voz IA, fotos reales, "
    "personaje animado y subtítulos)."
)

if "sql_server" not in st.secrets:
    st.error(
        "Falta configurar los secrets de la base de datos (`[sql_server]` con "
        "`server`, `database`, `user` y `password`). Sin esto la app no puede "
        "generar ningún video. Ver README.md, sección 'Base de datos SQL Server'."
    )
    st.stop()

_write_local_secrets()

try:
    sql_database.get_connection_required().close()
except sql_database.ErrorConexionSQL as exc:
    st.error(f"No se pudo conectar a la base de datos: {exc}")
    st.stop()

HAS_DRIVE = "gdrive" in st.secrets
if not HAS_DRIVE:
    st.info("Sin secrets de `[gdrive]` configurados: el video se queda solo para descargar aquí, no se sube a Drive.")


def _generate_and_upload(source: str, trend_category: str | None = None, fact_id: str | None = None) -> None:
    try:
        service, folder_id = drive_sync.load_drive_service_from_config() if HAS_DRIVE else (None, None)

        with st.status("Generando video...", expanded=True) as status:
            st.write("Eligiendo dato, generando voz, fotos y personaje animado (1-3 min)...")
            out_path = generador_pipeline.main(source=source, trend_category=trend_category, fact_id=fact_id)
            caption_path = out_path.with_suffix(".txt")

            if service:
                st.write("Subiendo el video a Google Drive...")
                drive_sync.push_results_to_drive(service, folder_id, out_path, caption_path)

            status.update(label="¡Listo!", state="complete")

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
    st.caption("Elige un dato puntual de `[Pruebaa].[videosApp].[FactsBank]` o deja \"Al azar\".")
    try:
        unused_facts = generador_pipeline.list_unused_local_facts()
    except sql_database.ErrorConexionSQL:
        unused_facts = []
        st.warning("No se pudo leer el banco local ahora mismo.")
    AL_AZAR = "Al azar"
    fact_options = [AL_AZAR] + [f["id"] for f in unused_facts]
    fact_labels = {AL_AZAR: AL_AZAR}
    fact_labels.update({f["id"]: f"[{f['category']}] {f['text'][:55]}..." for f in unused_facts})
    local_fact_choice = st.selectbox(
        "Dato", fact_options, format_func=lambda x: fact_labels[x], label_visibility="collapsed"
    )
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
    chosen_id = None if local_fact_choice == AL_AZAR else local_fact_choice
    _generate_and_upload(source="local", fact_id=chosen_id)
elif games_clicked:
    _generate_and_upload(source="games")
elif trending_clicked:
    category = None if trend_category_choice == "Cualquiera" else trend_category_choice
    _generate_and_upload(source="trending", trend_category=category)
