"""
Guarda/lee archivos en una carpeta de Google Drive. Se usa para que los
videos generados y el registro de "no repetir" (used_facts.json,
used_wikipedia.json) sobrevivan aunque la app en la nube (Streamlit Cloud)
se reinicie y borre su disco local — Drive actúa como almacenamiento
persistente externo.

Requiere una cuenta de servicio de Google Cloud con acceso a la API de
Drive, compartida como "Editor" en la carpeta de destino. Ver README.md
para la guía paso a paso de cómo crearla.
"""

import io

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]


def get_service(service_account_info: dict):
    """Crea el cliente de la API de Drive a partir del JSON de la cuenta de
    servicio (tal como se guarda en Streamlit secrets)."""
    creds = service_account.Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def _find_file_id(service, folder_id: str, filename: str) -> str | None:
    query = f"'{folder_id}' in parents and name = '{filename}' and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get("files", [])
    return files[0]["id"] if files else None


def download_file(service, folder_id: str, filename: str) -> bytes | None:
    """Devuelve el contenido del archivo, o None si no existe en esa carpeta."""
    file_id = _find_file_id(service, folder_id, filename)
    if not file_id:
        return None
    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue()


def upload_file(service, folder_id: str, filename: str, content: bytes, mime_type: str) -> str:
    """Sube el archivo a la carpeta; si ya existe uno con el mismo nombre,
    lo reemplaza (actualiza) en vez de duplicarlo. Devuelve el ID del archivo."""
    media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type, resumable=True)
    existing_id = _find_file_id(service, folder_id, filename)

    if existing_id:
        service.files().update(fileId=existing_id, media_body=media).execute()
        return existing_id

    file_metadata = {"name": filename, "parents": [folder_id]}
    created = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    return created["id"]
