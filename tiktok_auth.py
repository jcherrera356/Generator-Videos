"""
Autoriza esta app de TikTok (OAuth2) para poder publicar videos via la
Content Posting API oficial. Se corre UNA sola vez (o de nuevo si el
refresh_token llega a expirar): abre tu navegador para que inicies sesion en
TikTok y apruebes los permisos, y guarda el token resultante en
tiktok_tokens.json.

Antes de correrlo:
  1. Completa tiktok_config.json con tu client_key, client_secret y el
     redirect_uri EXACTO que registraste en developers.tiktok.com para esta
     app (debe coincidir caracter por caracter).
  2. El redirect_uri debe apuntar a localhost con un puerto libre, por
     ejemplo http://localhost:8721/callback (ese es el valor por defecto).
"""

import json
import secrets
import sys
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "tiktok_config.json"
TOKENS_FILE = BASE_DIR / "tiktok_tokens.json"

SCOPES = "user.info.basic,video.publish"

_result: dict = {}


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        _result["code"] = params.get("code", [None])[0]
        _result["state"] = params.get("state", [None])[0]
        _result["error"] = params.get("error", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        message = "Listo, ya puedes cerrar esta pestaña y volver a la terminal."
        if _result.get("error"):
            message = f"TikTok devolvió un error: {_result['error']}. Cierra esta pestaña y revisa la terminal."
        self.wfile.write(f"<h2>{message}</h2>".encode("utf-8"))

    def log_message(self, format: str, *args) -> None:  # silencia logs del server
        pass


def main() -> None:
    if not CONFIG_FILE.exists():
        print(f"[ERROR] No existe {CONFIG_FILE}. Complétalo primero.", file=sys.stderr)
        sys.exit(1)

    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    client_key = config.get("client_key", "").strip()
    client_secret = config.get("client_secret", "").strip()
    redirect_uri = config.get("redirect_uri", "").strip()

    if not client_key or not client_secret or not redirect_uri:
        print("[ERROR] Completa client_key, client_secret y redirect_uri en tiktok_config.json.", file=sys.stderr)
        sys.exit(1)

    state = secrets.token_urlsafe(16)
    parsed_redirect = urllib.parse.urlparse(redirect_uri)
    port = parsed_redirect.port or 80

    auth_url = "https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode(
        {
            "client_key": client_key,
            "response_type": "code",
            "scope": SCOPES,
            "redirect_uri": redirect_uri,
            "state": state,
        }
    )

    server = HTTPServer(("localhost", port), CallbackHandler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    print("[+] Abriendo el navegador para que inicies sesión en TikTok y autorices la app...")
    print(f"    Si no se abre solo, entra manualmente a:\n    {auth_url}\n")
    webbrowser.open(auth_url)
    thread.join(timeout=300)

    if _result.get("error"):
        print(f"[ERROR] TikTok rechazó la autorización: {_result['error']}", file=sys.stderr)
        sys.exit(1)

    code = _result.get("code")
    if not code:
        print("[ERROR] No se recibió el código de autorización (tiempo agotado o cancelado).", file=sys.stderr)
        sys.exit(1)
    if _result.get("state") != state:
        print("[ERROR] El parámetro 'state' no coincide; posible intento de interceptación. Abortando.", file=sys.stderr)
        sys.exit(1)

    token_response = requests.post(
        "https://open.tiktokapis.com/v2/oauth/token/",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        timeout=15,
    )
    tokens = token_response.json()
    if token_response.status_code != 200 or "access_token" not in tokens:
        print(f"[ERROR] TikTok no devolvió un token válido:\n{json.dumps(tokens, indent=2)}", file=sys.stderr)
        sys.exit(1)

    TOKENS_FILE.write_text(json.dumps(tokens, indent=2), encoding="utf-8")
    print(f"[OK] Autorización completada. Tokens guardados en {TOKENS_FILE}")


if __name__ == "__main__":
    main()
