"""
Genera un clip de video con el rostro sintetico (avatar_face.png) hablando,
sincronizando los labios con el audio narrado, usando Wav2Lip (GPU/CUDA).

Se ejecuta con el interprete del entorno virtual avatar_env, por separado del
resto del pipeline (que no necesita PyTorch), y se invoca via subprocess desde
generate_video.py.

Uso: python lipsync_avatar.py <audio.wav|mp3> <salida.mp4> [imagen_rostro.png]
"""

import sys
from pathlib import Path

from lipsync import LipSync

BASE_DIR = Path(__file__).resolve().parent
CHECKPOINT = BASE_DIR / "weights" / "wav2lip_gan.pth"
DEFAULT_FACE = BASE_DIR / "avatar_face.png"


def main() -> None:
    if len(sys.argv) < 3:
        print("Uso: python lipsync_avatar.py <audio> <salida.mp4> [rostro.png]", file=sys.stderr)
        sys.exit(1)

    audio_path = sys.argv[1]
    out_path = sys.argv[2]
    face_path = sys.argv[3] if len(sys.argv) > 3 else str(DEFAULT_FACE)

    lip = LipSync(
        model="wav2lip",
        checkpoint_path=str(CHECKPOINT),
        device="cuda",
    )
    lip.sync(face_path, audio_path, out_path)
    print(f"[OK] Video con lip-sync generado: {out_path}")


if __name__ == "__main__":
    main()
