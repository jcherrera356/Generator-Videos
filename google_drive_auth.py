"""
Autoriza el acceso a TU Google Drive (una sola vez, se corre en tu PC, no
en Streamlit Cloud). Las cuentas de servicio de Google no pueden crear
archivos en un Drive personal (no tienen cuota de almacenamiento propia),
así que en vez de eso la app actúa "como tú" usando este token.

Antes de correrlo:
  1. En https://console.cloud.google.com/ (mismo proyecto de antes), ve a
     "Credenciales" → "Crear credenciales" → "ID de cliente de OAuth".
  2. Tipo de aplicación: "Aplicación de escritorio". Créala.
  3. Descarga el JSON (botón de descarga en la credencial recién creada) y
     guárdalo en esta carpeta como oauth_client.json.
  4. Corre: python google_drive_auth.py
  5. Se abre tu navegador, inicias sesión con la cuenta dueña de la carpeta
     de Drive, y aceptas el permiso.
  6. Copia los 3 valores que imprime al final en los Secrets de Streamlit.
"""

import json
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

BASE_DIR = Path(__file__).resolve().parent
CLIENT_SECRET_FILE = BASE_DIR / "oauth_client.json"
SCOPES = ["https://www.googleapis.com/auth/drive"]


def main() -> None:
    if not CLIENT_SECRET_FILE.exists():
        print(f"[ERROR] No existe {CLIENT_SECRET_FILE}. Sigue los pasos del docstring de este archivo.", file=sys.stderr)
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_FILE), SCOPES)
    creds = flow.run_local_server(port=0)

    client_config = json.loads(CLIENT_SECRET_FILE.read_text(encoding="utf-8"))
    client_info = client_config.get("installed") or client_config.get("web")

    print("\n[OK] Autorización completada. Pega esto en Streamlit → Settings → Secrets:\n")
    print("[gdrive]")
    print(f'folder_id = "TU_ID_DE_CARPETA_AQUI"')
    print(f'client_id = "{client_info["client_id"]}"')
    print(f'client_secret = "{client_info["client_secret"]}"')
    print(f'refresh_token = "{creds.refresh_token}"')


if __name__ == "__main__":
    main()
