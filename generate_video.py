"""
Generador automático de videos verticales de "datos curiosos" para TikTok.

Pipeline por cada ejecución:
  1. Elige un dato curioso no usado del banco (facts_bank.json).
  2. Genera narración con voz IA (edge-tts, gratuito) y captura el timing
     de cada palabra para subtítulos sincronizados.
  3. Busca fotos reales relacionadas al tema (API gratuita de Pexels) — una
     por cada segmento/oración del relato, para que la imagen vaya cambiando
     a medida que se habla. Si no hay fotos disponibles, usa un ícono
     ilustrado de respaldo (visuals.py).
  4. Arma el fondo de pantalla completa a partir de esa misma foto (borrosa
     y oscurecida) con efecto Ken Burns; sin foto, usa un degradado.
  5. Genera un personaje animado de cuerpo completo (brazos, piernas, ropa
     al azar) que realiza una acción distinta por video (caminar, saludar,
     señalar, explicar con las manos), con la boca sincronizada al audio.
  6. Compone todas las capas + subtítulos karaoke con ffmpeg.
  7. Mezcla la narración con música de fondo (si hay archivos en music/).
  8. Exporta el video final a output/ listo para publicar.

Requiere: ffmpeg en el PATH, y edge-tts/pillow/requests/numpy instalados.
La subida a TikTok NO está incluida aquí: debe hacerse manualmente o vía
la TikTok Content Posting API oficial, para no violar los Términos de Servicio.
"""

import asyncio
import json
import random
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# La consola de Windows a veces usa una codificación antigua (cp1252) que no
# soporta ciertos acentos/caracteres (frecuentes en títulos de Wikipedia en
# otros idiomas): sin esto, un simple print() puede tumbar el script.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

import edge_tts
from PIL import Image, ImageEnhance, ImageFilter

import groq_client
import pexels_photos
import rawg_games
import visuals
import wikipedia_facts

BASE_DIR = Path(__file__).resolve().parent
FACTS_FILE = BASE_DIR / "facts_bank.json"
USED_FILE = BASE_DIR / "used_facts.json"
MUSIC_DIR = BASE_DIR / "music"
OUTPUT_DIR = BASE_DIR / "output"
TMP_DIR = BASE_DIR / "tmp"

VOICE = "es-MX-JorgeNeural"
WIDTH, HEIGHT = 1080, 1920
FPS = 30

# Varias frases de entrada/cierre para que no todos los videos suenen igual.
# "Sabías que..." puede salir (está en la lista), pero ya no es la única.
INTRO_PHRASES = [
    "Sabías que... ",
    "No vas a creer esto: ",
    "Dato curioso del día: ",
    "Prepárate para esto: ",
    "Esto te va a sorprender: ",
    "Un dato que casi nadie conoce: ",
    "Escucha esto con atención: ",
    "Hoy te cuento algo increíble: ",
    "Pocos saben esto, pero... ",
    "Atento a este dato: ",
]
OUTRO_PHRASES = [
    " Sígueme para más datos curiosos.",
    " Cuéntame en los comentarios si ya lo sabías.",
    " Compártelo si te sorprendió.",
    " Dale like si aprendiste algo nuevo hoy.",
    " Guarda este video para no olvidarlo.",
    " Sígueme si quieres aprender algo nuevo cada día.",
    " ¿Lo sabías? Dímelo en los comentarios.",
    " Comenta qué otro dato curioso quieres que cuente.",
]
MAX_TOPIC_SEGMENTS = 4
WIKIPEDIA_PROBABILITY = 0.5  # probabilidad de usar un dato de Wikipedia en vez del banco local

DEFAULT_HASHTAGS = [
    "#datoscuriosos", "#curiosidades", "#sabiasque", "#parati", "#viral",
    "#aprendeconTikTok", "#dato", "#datosinteresantes",
]

ICON_POS = ((WIDTH - visuals.ICON_SIZE) // 2, 150)
AVATAR_POS = ((WIDTH - visuals.CHAR_CARD_W) // 2, 1240)

GRADIENT_PALETTES = [
    ((20, 24, 82), (255, 94, 98)),
    ((10, 10, 40), (0, 191, 165)),
    ((36, 12, 74), (255, 138, 0)),
    ((5, 30, 60), (0, 200, 255)),
    ((60, 10, 40), (255, 60, 120)),
    ((15, 40, 20), (150, 255, 90)),
]


def load_facts() -> list[dict]:
    return json.loads(FACTS_FILE.read_text(encoding="utf-8"))


def load_used() -> list[str]:
    if USED_FILE.exists():
        return json.loads(USED_FILE.read_text(encoding="utf-8"))
    return []


def save_used(used: list[str]) -> None:
    USED_FILE.write_text(json.dumps(used, ensure_ascii=False, indent=2), encoding="utf-8")


def pick_fact_from_local() -> dict:
    """Elige un dato del banco fijo (facts_bank.json), sin repetir hasta
    agotarlo (ahí se reinicia el registro y vuelve a empezar)."""
    facts = load_facts()
    used = load_used()
    remaining = [f for f in facts if f["id"] not in used]
    if not remaining:
        used = []
        remaining = facts
    fact = random.choice(remaining)
    used.append(fact["id"])
    save_used(used)
    return fact


def pick_fact_from_wikipedia() -> dict:
    """Elige un dato nuevo y al azar desde Wikipedia (sin repetir artículos
    ya usados). Si Wikipedia falla (sin internet, sin resultados nuevos
    tras varios intentos, etc.), cae al banco local para no interrumpir
    la generación del video."""
    wiki_fact = wikipedia_facts.fetch_unused_fact()
    if wiki_fact:
        return wiki_fact
    print("[!] No se pudo traer un dato nuevo de Wikipedia, se usa el banco local.")
    return pick_fact_from_local()


def pick_fact_from_games() -> dict:
    """Elige un dato sobre un videojuego (API de RAWG), con sus propias
    fotos reales ya incluidas. Si RAWG falla (sin API key, sin internet,
    etc.), cae al banco local para no interrumpir la generación."""
    game_fact = rawg_games.fetch_unused_game()
    if game_fact:
        return game_fact
    print("[!] No se pudo traer un dato nuevo de RAWG, se usa el banco local.")
    return pick_fact_from_local()


def pick_fact(source: str = "auto") -> dict:
    """source: "wikipedia" (siempre Wikipedia, con respaldo al banco local
    si falla), "local" (siempre el banco fijo), "games" (siempre RAWG, con
    el mismo respaldo), o "auto" (por defecto: al azar entre Wikipedia y
    local según WIKIPEDIA_PROBABILITY, como antes)."""
    if source == "wikipedia":
        return pick_fact_from_wikipedia()
    if source == "games":
        return pick_fact_from_games()
    if source == "local":
        return pick_fact_from_local()

    if random.random() < WIKIPEDIA_PROBABILITY:
        return pick_fact_from_wikipedia()
    return pick_fact_from_local()


def make_gradient_image() -> Image.Image:
    top, bottom = random.choice(GRADIENT_PALETTES)
    img = Image.new("RGB", (WIDTH, HEIGHT))
    px = img.load()
    for y in range(HEIGHT):
        t = y / (HEIGHT - 1)
        r = round(top[0] + (bottom[0] - top[0]) * t)
        g = round(top[1] + (bottom[1] - top[1]) * t)
        b = round(top[2] + (bottom[2] - top[2]) * t)
        for x in range(WIDTH):
            px[x, y] = (r, g, b)
    return img


def make_background_source(photos: list[Image.Image]) -> Image.Image:
    """Fondo de pantalla completa: foto real borrosa/oscurecida, o degradado."""
    if not photos:
        return make_gradient_image()
    cover = pexels_photos.to_cover_rgb(photos[0], WIDTH, HEIGHT)
    blurred = cover.filter(ImageFilter.GaussianBlur(radius=35))
    return ImageEnhance.Brightness(blurred).enhance(0.55)


async def synthesize(text: str, audio_path: Path) -> list[dict]:
    """Genera el audio y devuelve el timing de cada palabra (en segundos)."""
    communicate = edge_tts.Communicate(text, VOICE, boundary="WordBoundary")
    word_boundaries = []
    with open(audio_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word_boundaries.append(
                    {
                        "text": chunk["text"],
                        "start": chunk["offset"] / 10_000_000,
                        "end": (chunk["offset"] + chunk["duration"]) / 10_000_000,
                    }
                )
    return word_boundaries


def group_words(words: list[dict], chunk_size: int = 4) -> list[dict]:
    chunks = []
    for i in range(0, len(words), chunk_size):
        group = words[i : i + chunk_size]
        chunks.append(
            {
                "text": " ".join(w["text"] for w in group).upper(),
                "start": group[0]["start"],
                "end": group[-1]["end"],
            }
        )
    return chunks


def split_script_segments(intro: str, fact_text: str, outro: str, words: list[dict]) -> list[tuple[int, int]]:
    """Divide el guion en tramos (por oración) para poder cambiar de imagen
    a medida que se habla. Devuelve rangos de índice sobre la lista `words`.
    """
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", fact_text.strip()) if s.strip()]
    if not sentences:
        return [(0, len(words))]

    intro_wc = len(intro.split())
    outro_wc = len(outro.split())
    n = len(sentences)

    segments = []
    idx = 0
    for i, sentence in enumerate(sentences):
        wc = len(sentence.split())
        if i == 0:
            wc += intro_wc
        if i == n - 1:
            wc += outro_wc
        end_idx = min(idx + wc, len(words))
        segments.append((idx, end_idx))
        idx = end_idx
    segments[-1] = (segments[-1][0], len(words))

    if len(segments) > MAX_TOPIC_SEGMENTS:
        merged = segments[: MAX_TOPIC_SEGMENTS - 1]
        merged.append((segments[MAX_TOPIC_SEGMENTS - 1][0], segments[-1][1]))
        segments = merged
    return segments


def segment_times(segments: list[tuple[int, int]], words: list[dict], duration: float) -> list[tuple[float, float]]:
    times = []
    for start_idx, end_idx in segments:
        t0 = words[start_idx]["start"] if start_idx < len(words) else 0.0
        t1 = words[end_idx - 1]["end"] if 0 <= end_idx - 1 < len(words) else duration
        times.append((t0, t1))
    if times:
        times[0] = (0.0, times[0][1])
        times[-1] = (times[-1][0], duration)
    return times


def fmt_ass_time(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def build_ass(chunks: list[dict], ass_path: Path) -> None:
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {WIDTH}
PlayResY: {HEIGHT}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,68,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,6,0,2,60,60,720,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for c in chunks:
        start = fmt_ass_time(c["start"])
        end = fmt_ass_time(c["end"])
        lines.append(
            f"Dialogue: 0,{start},{end},Default,,0,0,0,,{{\\fad(80,80)}}{c['text']}\n"
        )
    ass_path.write_text("".join(lines), encoding="utf-8")


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError(f"Comando falló: {' '.join(cmd)}")


def get_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def build_background_video(bg_png: Path, duration: float, out_path: Path) -> None:
    total_frames = max(1, int(duration * FPS))
    zoom_expr = "min(zoom+0.0006,1.25)"
    run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(bg_png),
            "-vf",
            f"scale=2160:3840,zoompan=z='{zoom_expr}':d={total_frames}:s={WIDTH}x{HEIGHT}:fps={FPS}",
            "-t",
            str(duration),
            "-pix_fmt",
            "yuv420p",
            str(out_path),
        ]
    )


def build_zoom_clip(image: Image.Image, duration: float, size: int, out_path: Path) -> None:
    """Clip cuadrado con efecto Ken Burns a partir de una sola imagen."""
    tmp_png = out_path.with_suffix(".src.png")
    image.save(tmp_png)
    duration = max(duration, 0.4)
    total_frames = max(1, int(duration * FPS))
    zoom_expr = "min(zoom+0.0009,1.3)"
    run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(tmp_png),
            "-vf",
            f"scale={size * 2}:{size * 2},zoompan=z='{zoom_expr}':d={total_frames}:s={size}x{size}:fps={FPS}",
            "-t",
            str(duration),
            "-pix_fmt",
            "yuv420p",
            str(out_path),
        ]
    )
    tmp_png.unlink(missing_ok=True)


def build_topic_video(fact: dict, photos: list[Image.Image], seg_times: list[tuple[float, float]], out_path: Path) -> None:
    """Video del tema: una serie de fotos (o el icono de respaldo) que van
    cambiando a lo largo del relato, cada una con su propio zoom Ken Burns.
    """
    if not photos:
        img = visuals.make_icon_card(fact["category"]).convert("RGB")
        total_duration = seg_times[-1][1] if seg_times else 1.0
        build_zoom_clip(img, total_duration, visuals.ICON_SIZE, out_path)
        return

    clip_paths = []
    for i, (t0, t1) in enumerate(seg_times):
        photo = photos[i] if i < len(photos) else photos[-1]
        img = pexels_photos.to_cover_rgb(photo, visuals.ICON_SIZE, visuals.ICON_SIZE)
        clip_path = TMP_DIR / f"topic_seg_{i}.mp4"
        build_zoom_clip(img, t1 - t0, visuals.ICON_SIZE, clip_path)
        clip_paths.append(clip_path)

    if len(clip_paths) == 1:
        clip_paths[0].replace(out_path)
        return

    concat_list = TMP_DIR / "topic_concat.txt"
    concat_list.write_text(
        "\n".join(f"file '{p.resolve().as_posix()}'" for p in clip_paths), encoding="utf-8"
    )
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(out_path)])


def build_audio(tts_path: Path, duration: float, out_path: Path) -> None:
    music_files = list(MUSIC_DIR.glob("*.mp3")) + list(MUSIC_DIR.glob("*.wav"))
    if not music_files:
        out_path.write_bytes(tts_path.read_bytes())
        return
    music = random.choice(music_files)
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(music),
            "-i",
            str(tts_path),
            "-filter_complex",
            (
                f"[0:a]aloop=loop=-1:size=2e9,atrim=0:{duration},volume=0.18[bg];"
                f"[1:a]volume=1.4[voice];"
                f"[bg][voice]amix=inputs=2:duration=first:dropout_transition=2[aout]"
            ),
            "-map",
            "[aout]",
            str(out_path),
        ]
    )


def render_final(
    bg_video: Path,
    topic_video: Path,
    topic_mask: Path,
    char_frames_dir: Path,
    audio: Path,
    ass_path: Path,
    out_path: Path,
) -> None:
    ass_escaped = str(ass_path).replace("\\", "/").replace(":", "\\:")
    ix, iy = ICON_POS
    ax, ay = AVATAR_POS
    size = visuals.ICON_SIZE
    filter_complex = (
        f"[1:v]scale={size}:{size}[topic_scaled];"
        f"[topic_scaled][2:v]alphamerge[topic_rounded];"
        f"[0:v][topic_rounded]overlay={ix}:{iy}[v1];"
        f"[v1][3:v]overlay={ax}:{ay}[v2];"
        f"[v2]subtitles='{ass_escaped}'[vout]"
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(bg_video),
            "-i",
            str(topic_video),
            "-loop",
            "1",
            "-i",
            str(topic_mask),
            "-start_number",
            "0",
            "-framerate",
            str(FPS),
            "-i",
            str(char_frames_dir / "frame_%05d.png"),
            "-i",
            str(audio),
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            "4:a",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-c:a",
            "aac",
            "-shortest",
            str(out_path),
        ]
    )


def generate_caption(fact: dict) -> tuple[str, list[str]]:
    """Título corto sugerido + hashtags recomendados para subir el video a
    TikTok. Usa IA (Groq) para redactarlo con base en el dato del video; si
    no está disponible, arma algo razonable con reglas simples.
    """
    system_prompt = (
        "Eres un experto en growth de TikTok en español. Respondes SIEMPRE "
        "en el formato exacto que se te pide, sin explicaciones ni texto de más."
    )
    user_prompt = (
        f'Dato curioso del video: "{fact["text"]}"\n\n'
        "Dame:\n"
        "1. Un título corto y llamativo para el video (máximo 60 caracteres, "
        "en español, sin comillas, pensado para enganchar en TikTok).\n"
        "2. Entre 8 y 12 hashtags relevantes en español, mezclando generales "
        "(ej. #datoscuriosos #parati #viral) con específicos del tema del dato.\n\n"
        "Responde EXACTAMENTE en este formato, sin nada más:\n"
        "TITULO: <el título>\n"
        "HASHTAGS: #tag1 #tag2 #tag3 ..."
    )
    reply = groq_client.chat(system_prompt, user_prompt, max_tokens=200)

    title = None
    hashtags: list[str] = []
    if reply:
        title_match = re.search(r"T[IÍ]TULO:\s*(.+)", reply, re.IGNORECASE)
        hashtags_match = re.search(r"HASHTAGS:\s*(.+)", reply, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip().strip('"')
        if hashtags_match:
            hashtags = re.findall(r"#\w+", hashtags_match.group(1))

    if not title:
        title = fact["text"][:60].rsplit(" ", 1)[0] + "..."
    if not hashtags:
        keyword_tag = "#" + re.sub(r"[^a-zA-Z0-9]", "", fact.get("keywords", fact["category"]))
        hashtags = DEFAULT_HASHTAGS + ([keyword_tag] if len(keyword_tag) > 1 else [])

    return title, hashtags


def save_caption_file(video_path: Path, title: str, hashtags: list[str], fact: dict | None = None) -> Path:
    caption_path = video_path.with_suffix(".txt")
    content = f"{title}\n\n{' '.join(hashtags)}\n"
    if fact and fact.get("category") == "videojuegos":
        # Requisito del plan gratuito de RAWG: atribuir la fuente con un
        # link activo donde se use su data/imágenes.
        content += "\nDatos e imágenes de videojuegos: RAWG (https://rawg.io)\n"
    caption_path.write_text(content, encoding="utf-8")
    return caption_path


def main(source: str = "auto") -> Path:
    """source: "wikipedia", "local", o "auto" (mitad y mitad) — ver pick_fact()."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    TMP_DIR.mkdir(exist_ok=True)
    MUSIC_DIR.mkdir(exist_ok=True)

    fact = pick_fact(source)
    intro = random.choice(INTRO_PHRASES)
    outro = random.choice(OUTRO_PHRASES)
    script_text = f"{intro}{fact['text']}{outro}"
    print(f"[+] Dato elegido: {fact['id']}")

    tts_path = TMP_DIR / "tts.mp3"
    words = asyncio.run(synthesize(script_text, tts_path))
    duration = get_duration(tts_path)
    print(f"[+] Narración generada ({duration:.1f}s)")

    chunks = group_words(words, chunk_size=4)
    ass_path = TMP_DIR / "captions.ass"
    build_ass(chunks, ass_path)

    segments = split_script_segments(intro, fact["text"], outro, words)
    seg_times = segment_times(segments, words, duration)

    if fact.get("photos"):
        # Ya vienen incluidas (ej. capturas reales de RAWG) - no hace falta Pexels.
        photos = fact["photos"]
        print(f"[+] {len(photos)} foto(s) real(es) ya incluida(s) con el dato ({fact.get('keywords')})")
    else:
        photos = pexels_photos.fetch_topic_photos(fact.get("keywords", fact["category"]), len(seg_times))
        if photos:
            print(f"[+] {len(photos)} foto(s) real(es) obtenida(s) ({fact.get('keywords')})")
        else:
            print(f"[+] Sin fotos reales disponibles, se usará el ícono ilustrado ({fact['category']})")

    bg_png = TMP_DIR / "bg.png"
    make_background_source(photos).save(bg_png)
    bg_video = TMP_DIR / "bg.mp4"
    build_background_video(bg_png, duration, bg_video)
    print("[+] Fondo animado generado")

    topic_video = TMP_DIR / "topic.mp4"
    build_topic_video(fact, photos, seg_times, topic_video)
    print(f"[+] Video del tema generado ({len(seg_times)} imagen(es))")

    topic_mask = TMP_DIR / "topic_mask.png"
    visuals.make_rounded_mask(visuals.ICON_SIZE, visuals.ICON_SIZE, visuals.CARD_RADIUS).save(topic_mask)

    total_frames = max(1, int(duration * FPS))
    char_dir = TMP_DIR / "character_frames"
    action = visuals.render_character_frames(tts_path, total_frames, FPS, char_dir)
    print(f"[+] Personaje animado generado (acción: {action})")

    mixed_audio = TMP_DIR / "mixed.mp3"
    build_audio(tts_path, duration, mixed_audio)
    print("[+] Audio mezclado")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUT_DIR / f"dato_curioso_{timestamp}_{fact['id']}.mp4"
    render_final(bg_video, topic_video, topic_mask, char_dir, mixed_audio, ass_path, out_path)

    title, hashtags = generate_caption(fact)
    if fact.get("category") == "videojuegos":
        for extra_tag in ("#videojuegos", "#gaming"):
            if extra_tag not in hashtags:
                hashtags.append(extra_tag)
    caption_path = save_caption_file(out_path, title, hashtags, fact)

    print(f"[OK] Video listo: {out_path}")
    print(f"[OK] Título/hashtags sugeridos ({caption_path.name}):")
    print(f"     {title}")
    print(f"     {' '.join(hashtags)}")
    return out_path


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
