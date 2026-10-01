"""
Elementos visuales generados localmente con PIL, sin necesidad de internet
ni modelos de IA: tarjetas de icono por tema y un avatar animado simple
(boca sincronizada al volumen de la voz, parpadeo ocasional).
"""

import math
import random
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ICON_SIZE = 640
AVATAR_SIZE = 480  # tamaño del avatar simple (respaldo)
CHAR_CARD_W = 440  # tamaño del personaje elaborado (cuerpo completo)
CHAR_CARD_H = 640
CARD_RADIUS = 64
CARD_COLOR = (16, 18, 32)
CARD_ALPHA = 235


def _card(width: int, height: int | None = None) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    height = width if height is None else height
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        [0, 0, width - 1, height - 1], radius=CARD_RADIUS, fill=(*CARD_COLOR, CARD_ALPHA)
    )
    return img, draw


def _star(cx: float, cy: float, r: float) -> list[tuple[float, float]]:
    pts = []
    for i in range(8):
        angle = math.pi / 4 * i
        radius = r if i % 2 == 0 else r * 0.4
        pts.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return pts


def _icon_espacio(draw: ImageDraw.ImageDraw) -> None:
    cx, cy = 320, 340
    draw.ellipse([cx - 150, cy - 150, cx + 150, cy + 150], fill=(255, 159, 67, 255))
    draw.ellipse([cx - 190, cy - 45, cx + 190, cy + 15], outline=(255, 255, 255, 255), width=10)
    for sx, sy, r in [(140, 150, 16), (500, 190, 11), (470, 470, 18), (150, 500, 12)]:
        draw.polygon(_star(sx, sy, r), fill=(255, 255, 255, 255))


def _icon_oceano(draw: ImageDraw.ImageDraw) -> None:
    for i, yoff in enumerate([420, 465, 510]):
        pts = [(x, yoff + 18 * math.sin(x / 40 + i)) for x in range(60, 580, 10)]
        draw.line(pts, fill=(102, 204, 255, 255), width=10, joint="curve")
    cx, cy = 320, 250
    draw.ellipse([cx - 90, cy - 55, cx + 70, cy + 55], fill=(255, 255, 255, 255))
    draw.polygon([(cx + 60, cy - 45), (cx + 140, cy), (cx + 60, cy + 45)], fill=(255, 255, 255, 255))
    draw.ellipse([cx - 60, cy - 16, cx - 38, cy + 6], fill=(20, 20, 20, 255))


def _icon_animales(draw: ImageDraw.ImageDraw) -> None:
    cx, cy = 320, 380
    draw.ellipse([cx - 95, cy - 40, cx + 95, cy + 130], fill=(255, 255, 255, 255))
    for dx, dy in [(-115, -150), (-42, -205), (42, -205), (115, -150)]:
        draw.ellipse([cx + dx - 46, cy + dy - 46, cx + dx + 46, cy + dy + 46], fill=(255, 255, 255, 255))


def _icon_insectos(draw: ImageDraw.ImageDraw) -> None:
    cx, cy = 320, 350
    draw.ellipse([cx - 90, cy + 20, cx + 90, cy + 180], fill=(100, 190, 70, 255))
    draw.ellipse([cx - 70, cy - 70, cx + 70, cy + 40], fill=(140, 220, 90, 255))
    draw.ellipse([cx - 50, cy - 150, cx + 50, cy - 65], fill=(180, 255, 120, 255))
    for sign in (-1, 1):
        draw.line([cx + sign * 35, cy - 110, cx + sign * 100, cy - 175], fill=(20, 20, 20, 255), width=7)
        for i in range(3):
            y = cy - 10 + i * 55
            draw.line([cx + sign * 65, y, cx + sign * 150, y - 25], fill=(20, 20, 20, 255), width=8)


def _icon_cuerpo(draw: ImageDraw.ImageDraw) -> None:
    cx, cy = 320, 330
    draw.ellipse([cx - 150, cy - 130, cx + 150, cy + 130], fill=(255, 182, 193, 255))
    for i in range(4):
        y = cy - 75 + i * 48
        draw.arc([cx - 125, y - 26, cx + 125, y + 26], start=200, end=340, fill=(200, 120, 140, 255), width=9)


def _icon_historia(draw: ImageDraw.ImageDraw) -> None:
    base_y = 470
    draw.polygon([(190, base_y - 160), (450, base_y - 160), (320, base_y - 265)], fill=(255, 255, 255, 255))
    draw.rectangle([180, base_y - 160, 460, base_y - 128], fill=(255, 255, 255, 255))
    for x in [210, 275, 340, 405]:
        draw.rectangle([x, base_y - 128, x + 32, base_y], fill=(255, 255, 255, 255))
    draw.rectangle([170, base_y, 470, base_y + 32], fill=(255, 255, 255, 255))


def _icon_tecnologia(draw: ImageDraw.ImageDraw) -> None:
    cx, cy = 320, 410
    for r in (190, 130, 70):
        draw.arc([cx - r, cy - r, cx + r, cy + r], start=215, end=325, fill=(120, 220, 255, 255), width=18)
    draw.ellipse([cx - 20, cy + 34, cx + 20, cy + 74], fill=(120, 220, 255, 255))


def _icon_clima(draw: ImageDraw.ImageDraw) -> None:
    cx, cy = 320, 300
    for dx, dy, r in [(-85, 15, 72), (0, -25, 92), (95, 15, 72), (0, 45, 82)]:
        draw.ellipse([cx + dx - r, cy + dy - r, cx + dx + r, cy + dy + r], fill=(255, 255, 255, 255))
    draw.polygon(
        [(330, 380), (280, 470), (320, 470), (270, 560), (360, 440), (315, 440)],
        fill=(255, 214, 0, 255),
    )


def _icon_comida(draw: ImageDraw.ImageDraw) -> None:
    cx, cy = 320, 370
    draw.ellipse([cx - 115, cy - 85, cx + 115, cy + 145], fill=(230, 60, 60, 255))
    draw.rectangle([cx - 10, cy - 150, cx + 10, cy - 85], fill=(120, 80, 40, 255))
    draw.polygon([(cx + 10, cy - 140), (cx + 75, cy - 170), (cx + 30, cy - 105)], fill=(90, 200, 90, 255))


def _icon_general(draw: ImageDraw.ImageDraw) -> None:
    """Bombillo de idea: respaldo para temas de Wikipedia sin categoría clara."""
    cx, cy = 320, 330
    draw.ellipse([cx - 110, cy - 130, cx + 110, cy + 90], fill=(255, 214, 92, 255))
    draw.rectangle([cx - 45, cy + 70, cx + 45, cy + 130], fill=(180, 180, 190, 255))
    for i in range(3):
        y = cy + 135 + i * 16
        draw.rectangle([cx - 45, y, cx + 45, y + 8], fill=(140, 140, 150, 255))
    for angle_deg in (200, 250, 290, 340):
        rad = math.radians(angle_deg)
        x1, y1 = cx + 130 * math.cos(rad), cy - 20 + 130 * math.sin(rad)
        x2, y2 = cx + 175 * math.cos(rad), cy - 20 + 175 * math.sin(rad)
        draw.line([x1, y1, x2, y2], fill=(255, 255, 255, 255), width=10)


def _icon_videojuegos(draw: ImageDraw.ImageDraw) -> None:
    """Control de videojuegos simplificado."""
    cx, cy = 320, 350
    draw.rounded_rectangle([cx - 160, cy - 70, cx + 160, cy + 70], radius=60, fill=(90, 90, 100, 255))
    # cruceta izquierda
    draw.rectangle([cx - 125, cy - 15, cx - 85, cy + 15], fill=(230, 230, 235, 255))
    draw.rectangle([cx - 115, cy - 25, cx - 95, cy + 25], fill=(230, 230, 235, 255))
    # botones derecha
    for dx, dy, color in [(90, -20, (230, 90, 90)), (120, 10, (90, 170, 230)), (60, 10, (230, 200, 90)), (90, 35, (110, 200, 120))]:
        draw.ellipse([cx + dx - 14, cy + dy - 14, cx + dx + 14, cy + dy + 14], fill=(*color, 255))


_ICON_DRAWERS = {
    "espacio": _icon_espacio,
    "oceano": _icon_oceano,
    "animales": _icon_animales,
    "insectos": _icon_insectos,
    "cuerpo": _icon_cuerpo,
    "historia": _icon_historia,
    "tecnologia": _icon_tecnologia,
    "clima": _icon_clima,
    "comida": _icon_comida,
    "general": _icon_general,
    "videojuegos": _icon_videojuegos,
}


def make_icon_card(category: str) -> Image.Image:
    img, draw = _card(ICON_SIZE)
    drawer = _ICON_DRAWERS.get(category, _icon_espacio)
    drawer(draw)
    return img


def make_rounded_mask(width: int, height: int | None = None, radius: int = CARD_RADIUS) -> Image.Image:
    """Mascara en escala de grises (blanco=opaco) para redondear esquinas."""
    height = width if height is None else height
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, width - 1, height - 1], radius=radius, fill=255)
    return mask


# ---------------------------------------------------------------------------
# Avatar simple (respaldo): solo cabeza con boca sincronizada al volumen


def make_avatar_base() -> Image.Image:
    img, draw = _card(AVATAR_SIZE)
    body_r = 170
    cx, cy = AVATAR_SIZE // 2, AVATAR_SIZE // 2 + 10
    draw.ellipse(
        [cx - body_r, cy - body_r, cx + body_r, cy + body_r],
        fill=(255, 209, 102, 255),
        outline=(20, 20, 20, 255),
        width=6,
    )
    return img


def draw_avatar_frame(base: Image.Image, mouth_state: int, blink: bool) -> Image.Image:
    frame = base.copy()
    draw = ImageDraw.Draw(frame)
    cx, cy = AVATAR_SIZE // 2, AVATAR_SIZE // 2 + 10
    eye_y = cy - 55
    eye_dx = 60
    eye_r = 26
    for sign in (-1, 1):
        ex = cx + sign * eye_dx
        if blink:
            draw.arc([ex - eye_r, eye_y - 6, ex + eye_r, eye_y + 20], start=200, end=340, fill=(20, 20, 20, 255), width=7)
        else:
            draw.ellipse([ex - eye_r, eye_y - eye_r, ex + eye_r, eye_y + eye_r], fill=(255, 255, 255, 255), outline=(20, 20, 20, 255), width=3)
            pupil_r = 11
            draw.ellipse([ex - pupil_r, eye_y - pupil_r, ex + pupil_r, eye_y + pupil_r], fill=(20, 20, 20, 255))

    mouth_y = cy + 60
    if mouth_state == 0:
        draw.line([cx - 35, mouth_y, cx + 35, mouth_y], fill=(20, 20, 20, 255), width=9)
    elif mouth_state == 1:
        draw.ellipse([cx - 26, mouth_y - 14, cx + 26, mouth_y + 14], fill=(40, 20, 20, 255))
    else:
        draw.ellipse([cx - 38, mouth_y - 30, cx + 38, mouth_y + 30], fill=(40, 20, 20, 255))
        draw.ellipse([cx - 22, mouth_y - 4, cx + 22, mouth_y + 18], fill=(200, 90, 100, 255))
    return frame


def compute_mouth_and_blinks(tts_path: Path, total_frames: int, fps: int) -> tuple[list[int], list[bool]]:
    """Analiza el volumen del audio narrado para animar la boca del avatar."""
    result = subprocess.run(
        ["ffmpeg", "-i", str(tts_path), "-f", "s16le", "-ar", "16000", "-ac", "1", "-"],
        capture_output=True,
    )
    pcm = np.frombuffer(result.stdout, dtype=np.int16).astype(np.float32)
    sample_rate = 16000
    samples_per_frame = sample_rate / fps

    rms = np.zeros(total_frames)
    for i in range(total_frames):
        start = int(i * samples_per_frame)
        end = int((i + 1) * samples_per_frame)
        window = pcm[start:end]
        if len(window):
            rms[i] = np.sqrt(np.mean(window ** 2))
    max_rms = rms.max() or 1.0
    norm = rms / max_rms

    silence_thresh = 0.08
    mid_thresh = 0.35
    states: list[int] = []
    current = 0
    hold = 0
    for v in norm:
        target = 0 if v < silence_thresh else (1 if v < mid_thresh else 2)
        if target != current:
            hold += 1
            if hold >= 2:
                current = target
                hold = 0
        else:
            hold = 0
        states.append(current)

    blinks: list[bool] = []
    blink_countdown = 0
    next_blink = random.randint(70, 140)
    for i in range(total_frames):
        if blink_countdown > 0:
            blinks.append(True)
            blink_countdown -= 1
        else:
            blinks.append(False)
            if i >= next_blink:
                blink_countdown = 4
                next_blink = i + random.randint(70, 140)

    return states, blinks


def render_avatar_frames(tts_path: Path, total_frames: int, fps: int, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    states, blinks = compute_mouth_and_blinks(tts_path, total_frames, fps)
    base = make_avatar_base()
    for i in range(total_frames):
        frame = draw_avatar_frame(base, states[i], blinks[i])
        frame.save(out_dir / f"frame_{i:05d}.png")


# ---------------------------------------------------------------------------
# Personaje elaborado: cuerpo completo, brazos y piernas articulados, ropa
# aleatoria y una "accion" distinta por video (caminar, saludar, senalar,
# explicar con las manos). Todo dibujado por frame con formas de PIL, sin
# modelos de IA ni GPU.

SKIN_TONES = [(255, 224, 189), (240, 184, 160), (198, 134, 66), (141, 85, 36), (255, 205, 148)]
HAIR_COLORS = [(40, 30, 20), (80, 50, 20), (20, 20, 20), (120, 80, 40), (190, 170, 60), (170, 40, 40)]
SHIRT_COLORS = [(230, 57, 70), (69, 123, 157), (42, 157, 143), (244, 162, 97), (106, 76, 156), (38, 70, 83), (233, 196, 106)]
PANTS_COLORS = [(30, 30, 40), (60, 60, 70), (80, 60, 40), (20, 40, 60), (60, 25, 25)]

ACTIONS = ["camina", "saluda", "senala", "explica"]

_CX = CHAR_CARD_W // 2
_HEAD_R = 74
_HEAD_CY = 176
_SHOULDER_Y = 258
_HIP_Y = 420
_GROUND_Y = 600
_THIGH_LEN = 90
_SHIN_LEN = 88
_ARM_LEN = 148
_DOWN = math.pi / 2  # angulo "brazo/pierna colgando hacia abajo"


def random_outfit() -> dict:
    return {
        "skin": random.choice(SKIN_TONES),
        "hair": random.choice(HAIR_COLORS),
        "shirt": random.choice(SHIRT_COLORS),
        "pants": random.choice(PANTS_COLORS),
    }


def pose_for_action(action: str, t: float) -> dict:
    """Calcula los angulos de brazos/piernas (radianes) en el segundo t."""
    if action == "idle":
        return {
            "left_leg": _DOWN,
            "right_leg": _DOWN,
            "left_arm": _DOWN + 0.06 * math.sin(0.8 * t),
            "right_arm": _DOWN - 0.06 * math.sin(0.8 * t + 1.0),
            "knee_bend": 0.0,
            "bob": abs(math.sin(0.5 * t)) * 3,
        }
    if action == "camina":
        speed = 2 * math.pi * 1.6
        return {
            "left_leg": _DOWN + 0.5 * math.sin(speed * t),
            "right_leg": _DOWN + 0.5 * math.sin(speed * t + math.pi),
            "left_arm": _DOWN + 0.4 * math.sin(speed * t + math.pi),
            "right_arm": _DOWN + 0.4 * math.sin(speed * t),
            "knee_bend": 0.35,
            "bob": abs(math.sin(speed * t)) * 6,
        }
    if action == "saluda":
        return {
            "left_leg": _DOWN + 0.05 * math.sin(1.5 * t),
            "right_leg": _DOWN - 0.05 * math.sin(1.5 * t),
            "left_arm": _DOWN + 0.08 * math.sin(1.5 * t),
            "right_arm": -1.4 + 0.35 * math.sin(2 * math.pi * 1.8 * t),
            "knee_bend": 0.0,
            "bob": 0.0,
        }
    if action == "senala":
        prog = min(t / 1.2, 1.0)
        target = -0.9
        wobble = 0.05 * math.sin(2 * math.pi * 1.0 * t) if prog >= 1.0 else 0.0
        return {
            "left_leg": _DOWN,
            "right_leg": _DOWN,
            "left_arm": _DOWN + 0.05 * math.sin(1.2 * t),
            "right_arm": _DOWN + (target - _DOWN) * prog + wobble,
            "knee_bend": 0.0,
            "bob": 0.0,
        }
    # "explica": gesticula con ambas manos al hablar
    return {
        "left_leg": _DOWN,
        "right_leg": _DOWN,
        "left_arm": _DOWN - 0.5 + 0.15 * math.sin(2 * math.pi * 1.2 * t),
        "right_arm": _DOWN - 0.5 + 0.15 * math.sin(2 * math.pi * 1.2 * t + math.pi),
        "knee_bend": 0.0,
        "bob": 0.0,
    }


def make_character_card() -> Image.Image:
    img, _ = _card(CHAR_CARD_W, CHAR_CARD_H)
    return img


def draw_character_frame(
    card_bg: Image.Image,
    outfit: dict,
    pose: dict,
    mouth_state: int,
    blink: bool,
) -> Image.Image:
    img = card_bg.copy()
    draw = ImageDraw.Draw(img)
    bob = pose["bob"]
    hip_y = _HIP_Y - bob
    shoulder_y = _SHOULDER_Y - bob
    head_cy = _HEAD_CY - bob
    knee_bend = pose["knee_bend"]

    # piernas (dos segmentos: muslo + pantorrilla)
    # "side" refleja el angulo horizontalmente para el lado izquierdo, para
    # que ambas piernas/brazos se muevan hacia SU propio lado (no el mismo).
    for hip_x, angle, side in [(_CX - 35, pose["left_leg"], -1), (_CX + 35, pose["right_leg"], 1)]:
        shin_angle = angle + knee_bend * (1 if angle >= _DOWN else -1)
        knee = (hip_x + side * _THIGH_LEN * math.cos(angle), hip_y + _THIGH_LEN * math.sin(angle))
        foot = (knee[0] + side * _SHIN_LEN * math.cos(shin_angle), knee[1] + _SHIN_LEN * math.sin(shin_angle))
        draw.line([hip_x, hip_y, *knee], fill=(*outfit["pants"], 255), width=34)
        draw.line([*knee, *foot], fill=(*outfit["pants"], 255), width=30)
        draw.ellipse([knee[0] - 16, knee[1] - 16, knee[0] + 16, knee[1] + 16], fill=(*outfit["pants"], 255))
        draw.ellipse([foot[0] - 22, foot[1] - 13, foot[0] + 22, foot[1] + 13], fill=(25, 22, 20, 255))

    # torso
    draw.rounded_rectangle(
        [_CX - 72, shoulder_y, _CX + 72, hip_y + 24], radius=32, fill=(*outfit["shirt"], 255)
    )

    # brazos (un segmento, con mano)
    for shoulder_x, angle, side in [(_CX - 72, pose["left_arm"], -1), (_CX + 72, pose["right_arm"], 1)]:
        hand = (shoulder_x + side * _ARM_LEN * math.cos(angle), shoulder_y + 20 + _ARM_LEN * math.sin(angle))
        draw.line([shoulder_x, shoulder_y + 20, *hand], fill=(*outfit["shirt"], 255), width=30)
        draw.ellipse([hand[0] - 17, hand[1] - 17, hand[0] + 17, hand[1] + 17], fill=(*outfit["skin"], 255))

    # cabeza + cabello
    draw.ellipse(
        [_CX - _HEAD_R, head_cy - _HEAD_R, _CX + _HEAD_R, head_cy + _HEAD_R],
        fill=(*outfit["skin"], 255),
        outline=(20, 20, 20, 255),
        width=4,
    )
    draw.pieslice(
        [_CX - _HEAD_R - 4, head_cy - _HEAD_R - 14, _CX + _HEAD_R + 4, head_cy + _HEAD_R * 0.25],
        start=180,
        end=360,
        fill=(*outfit["hair"], 255),
    )

    # ojos
    eye_y = head_cy - 10
    eye_dx = 30
    eye_r = 13
    for sign in (-1, 1):
        ex = _CX + sign * eye_dx
        if blink:
            draw.arc([ex - eye_r, eye_y - 4, ex + eye_r, eye_y + 10], start=200, end=340, fill=(20, 20, 20, 255), width=5)
        else:
            draw.ellipse([ex - eye_r, eye_y - eye_r, ex + eye_r, eye_y + eye_r], fill=(255, 255, 255, 255), outline=(20, 20, 20, 255), width=2)
            pr = 6
            draw.ellipse([ex - pr, eye_y - pr, ex + pr, eye_y + pr], fill=(20, 20, 20, 255))

    # boca
    mouth_y = head_cy + 32
    if mouth_state == 0:
        draw.line([_CX - 18, mouth_y, _CX + 18, mouth_y], fill=(20, 20, 20, 255), width=6)
    elif mouth_state == 1:
        draw.ellipse([_CX - 14, mouth_y - 8, _CX + 14, mouth_y + 8], fill=(40, 20, 20, 255))
    else:
        draw.ellipse([_CX - 20, mouth_y - 17, _CX + 20, mouth_y + 17], fill=(40, 20, 20, 255))
        draw.ellipse([_CX - 12, mouth_y - 2, _CX + 12, mouth_y + 10], fill=(200, 90, 100, 255))

    return img


def render_character_frames(tts_path: Path, total_frames: int, fps: int, out_dir: Path) -> str:
    """Genera los frames del personaje completo. Devuelve la accion elegida."""
    out_dir.mkdir(parents=True, exist_ok=True)
    states, blinks = compute_mouth_and_blinks(tts_path, total_frames, fps)
    outfit = random_outfit()
    action = random.choice(ACTIONS)
    card_bg = make_character_card()
    for i in range(total_frames):
        t = i / fps
        pose = pose_for_action(action, t)
        frame = draw_character_frame(card_bg, outfit, pose, states[i], blinks[i])
        frame.save(out_dir / f"frame_{i:05d}.png")
    return action
