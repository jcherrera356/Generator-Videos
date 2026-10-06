"""
Autoriza el acceso a TU Google Drive (una sola vez, se corre en tu PC).
Las cuentas de servicio de Google no pueden crear archivos en un Drive
personal (no tienen cuota de almacenamiento propia), así que en vez de eso
el script actúa "como tú" usando este token.

Antes de correrlo:
  1. En https://console.cloud.google.com/ (mismo proyecto de antes), ve a
     "Credenciales" → "Crear credenciales" → "ID de cliente de OAuth".
  2. Tipo de aplicación: "Aplicación de escritorio". Créala.
  3. Descarga el JSON (botón de descarga en la credencial recién creada) y
     guárdalo en esta carpeta como oauth_client.json.
  4. Corre: python google_drive_auth.py
  5. Se abre tu navegador, inicias sesión con la cuenta dueña de la carpeta
     de Drive, y aceptas el permiso.
  6. Copia el bloque "gdrive" que imprime al final dentro de
     .config/config.json (ver datos/app_config.py), agregando el
     `folder_id` de la carpeta que quieras usar.
"""

import json
import sys
from pathlib import Path

# La consola de Windows a veces usa una codificación antigua (cp1252) que no
# soporta acentos ni flechas: sin esto, el print() de éxito puede tumbar el
# script justo al final, después de ya haber iniciado sesión.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from google_auth_oauthlib.flow import InstalledAppFlow

BASE_DIR = Path(__file__).resolve().parent
CLIENT_SECRET_FILE = BASE_DIR / "oauth_client.json"
RESULT_FILE = BASE_DIR / "gdrive_secrets_RESULTADO.txt"
SCOPES = ["https://www.googleapis.com/auth/drive"]


def main() -> None:
    if not CLIENT_SECRET_FILE.exists():
        print(f"[ERROR] No existe {CLIENT_SECRET_FILE}. Sigue los pasos del docstring de este archivo.", file=sys.stderr)
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_FILE), SCOPES)
    creds = flow.run_local_server(port=0)

    client_config = json.loads(CLIENT_SECRET_FILE.read_text(encoding="utf-8"))
    client_info = client_config.get("installed") or client_config.get("web")

    gdrive_block = {
        "folder_id": "TU_ID_DE_CARPETA_AQUI",
        "client_id": client_info["client_id"],
        "client_secret": client_info["client_secret"],
        "refresh_token": creds.refresh_token,
    }
    block = json.dumps({"gdrive": gdrive_block}, indent=2, ensure_ascii=False)

    # Se guarda en un archivo ADEMAS de imprimirse, por si la consola vuelve
    # a fallar - este archivo NO se sube a git (ver .gitignore).
    RESULT_FILE.write_text(block, encoding="utf-8")

    print("\n[OK] Autorizacion completada. Agrega esto dentro de .config/config.json:\n")
    print(block)
    print(f"\n(Tambien quedo guardado en {RESULT_FILE.name} por si acaso)")


if __name__ == "__main__":
    main()
