"""
Sube los videos generados (carpeta output/) a TikTok usando la Content
Posting API oficial. Requiere haber corrido tiktok_auth.py primero.

Importante: mientras tu app de TikTok no haya pasado la auditoría de
TikTok for Developers, la API solo permite publicar en modo "Solo yo"
(SELF_ONLY) — el video queda en tu cuenta como borrador privado que tú
mismo revisas y publicas desde la app de TikTok. Publicar directo y
público de forma automática requiere que TikTok audite la app primero.

Lleva registro de qué videos ya se subieron en uploaded.json, así que
puedes correr este script las veces que quieras: solo sube los nuevos.
"""

import json
import sys
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "tiktok_config.json"
TOKENS_FILE = BASE_DIR / "tiktok_tokens.json"
OUTPUT_DIR = BASE_DIR / "output"
UPLOADED_FILE = BASE_DIR / "uploaded.json"

# Cambia a "PUBLIC_TO_EVERYONE" (u otra opción que te devuelva
# query_creator_info) solo una vez que tu app haya sido auditada por TikTok.
PRIVACY_LEVEL = "SELF_ONLY"


def load_tokens() -> dict:
    if not TOKENS_FILE.exists():
        print("[ERROR] No hay tokens guardados. Corre primero: python tiktok_auth.py", file=sys.stderr)
        sys.exit(1)
    return json.loads(TOKENS_FILE.read_text(encoding="utf-8"))


def save_tokens(tokens: dict) -> None:
    TOKENS_FILE.write_text(json.dumps(tokens, indent=2), encoding="utf-8")


def refresh_tokens_if_needed() -> dict:
    tokens = load_tokens()
    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    response = requests.post(
        "https://open.tiktokapis.com/v2/oauth/token/",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": config["client_key"],
            "client_secret": config["client_secret"],
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
        },
        timeout=15,
    )
    new_tokens = response.json()
    if response.status_code == 200 and "access_token" in new_tokens:
        save_tokens(new_tokens)
        return new_tokens
    print(f"[!] No se pudo refrescar el token, se usará el actual. Respuesta: {new_tokens}")
    return tokens


def query_creator_info(access_token: str) -> dict:
    response = requests.post(
        "https://open.tiktokapis.com/v2/post/publish/creator_info/query/",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json; charset=UTF-8"},
        timeout=15,
    )
    response.raise_for_status()
    return response.json().get("data", {})


def load_uploaded() -> list[str]:
    if UPLOADED_FILE.exists():
        return json.loads(UPLOADED_FILE.read_text(encoding="utf-8"))
    return []


def save_uploaded(names: list[str]) -> None:
    UPLOADED_FILE.write_text(json.dumps(names, indent=2, ensure_ascii=False), encoding="utf-8")


def upload_video(video_path: Path, access_token: str, title: str) -> None:
    size = video_path.stat().st_size

    init_response = requests.post(
        "https://open.tiktokapis.com/v2/post/publish/video/init/",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
        json={
            "post_info": {
                "title": title,
                "privacy_level": PRIVACY_LEVEL,
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
                "video_cover_timestamp_ms": 1000,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": size,
                "chunk_size": size,
                "total_chunk_count": 1,
            },
        },
        timeout=30,
    )
    init_data = init_response.json()
    if init_response.status_code != 200 or "data" not in init_data:
        raise RuntimeError(f"Fallo al iniciar la publicación: {init_data}")

    upload_url = init_data["data"]["upload_url"]
    publish_id = init_data["data"]["publish_id"]

    with open(video_path, "rb") as f:
        video_bytes = f.read()

    put_response = requests.put(
        upload_url,
        headers={
            "Content-Type": "video/mp4",
            "Content-Range": f"bytes 0-{size - 1}/{size}",
        },
        data=video_bytes,
        timeout=180,
    )
    if put_response.status_code not in (200, 201):
        raise RuntimeError(f"Fallo al subir el archivo de video: {put_response.status_code} {put_response.text}")

    for _ in range(40):
        status_response = requests.post(
            "https://open.tiktokapis.com/v2/post/publish/status/fetch/",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json={"publish_id": publish_id},
            timeout=15,
        )
        status_data = status_response.json().get("data", {})
        status = status_data.get("status")
        print(f"    estado: {status}")
        if status == "PUBLISH_COMPLETE":
            return
        if status == "FAILED":
            raise RuntimeError(f"La publicación falló: {status_data}")
        time.sleep(3)
    raise RuntimeError("Tiempo de espera agotado revisando el estado de la publicación.")


def main() -> None:
    tokens = refresh_tokens_if_needed()
    access_token = tokens["access_token"]

    try:
        creator_info = query_creator_info(access_token)
        allowed = creator_info.get("privacy_level_options", [])
        if allowed and PRIVACY_LEVEL not in allowed:
            print(f"[!] Tu cuenta permite estos niveles de privacidad: {allowed} (no '{PRIVACY_LEVEL}').")
    except requests.RequestException as exc:
        print(f"[!] No se pudo consultar la info del creador (se continúa igual): {exc}")

    uploaded = load_uploaded()
    videos = sorted(OUTPUT_DIR.glob("*.mp4"))
    pending = [v for v in videos if v.name not in uploaded]

    if not pending:
        print("[+] No hay videos nuevos por subir.")
        return

    for video_path in pending:
        title = video_path.stem.replace("dato_curioso_", "").replace("_", " ")[:150]
        print(f"[+] Subiendo {video_path.name}...")
        try:
            upload_video(video_path, access_token, title)
        except Exception as exc:
            print(f"[ERROR] No se pudo subir {video_path.name}: {exc}", file=sys.stderr)
            continue
        uploaded.append(video_path.name)
        save_uploaded(uploaded)
        print(f"[OK] {video_path.name} subido en modo {PRIVACY_LEVEL}.")


if __name__ == "__main__":
    main()
