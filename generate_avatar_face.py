"""
Genera una imagen de rostro SINTÉTICO (nadie real) con Stable Diffusion local,
para usarla como cara del avatar animado por lip-sync. Se ejecuta una sola vez
(o cuando quieras cambiar el aspecto del avatar); el resultado se reutiliza en
todos los videos.
"""

import sys
from pathlib import Path

import torch
from diffusers import StableDiffusionPipeline

BASE_DIR = Path(__file__).resolve().parent
OUT_PATH = BASE_DIR / "avatar_face.png"

PROMPT = (
    "portrait photo of a friendly young latin american presenter, looking at camera, "
    "neutral mouth closed, studio lighting, plain light gray background, shoulders visible, "
    "sharp focus, high detail, 35mm photography"
)
NEGATIVE_PROMPT = (
    "text, watermark, logo, multiple people, hands, glasses, hat, deformed, blurry, "
    "extra fingers, bad anatomy, cartoon, illustration, painting"
)


def main() -> None:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[+] Usando dispositivo: {device}")

    pipe = StableDiffusionPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5",
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
    )
    pipe = pipe.to(device)

    generator = torch.Generator(device=device).manual_seed(42)
    image = pipe(
        PROMPT,
        negative_prompt=NEGATIVE_PROMPT,
        num_inference_steps=30,
        guidance_scale=7.5,
        height=512,
        width=512,
        generator=generator,
    ).images[0]

    image.save(OUT_PATH)
    print(f"[OK] Rostro sintetico guardado en: {OUT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
