"""
Viral YouTube Shorts Generator — Kinetic Typography Style
Uses ASS karaoke subtitles + FFmpeg drawtext for CapCut-style animation.
This is the format actual viral faceless channels use.
"""

import os
import re
import math
import json
import time
import textwrap
import random
import logging
import subprocess
import tempfile
from typing import List, Tuple, Optional

log = logging.getLogger(__name__)

WIDTH  = 1080
HEIGHT = 1920
FPS    = 30

ACCENT_CYAN   = (0, 212, 255)
ACCENT_YELLOW = (255, 220, 0)
ACCENT_RED    = (255, 50, 50)
BG_DARK       = (10, 10, 15)

# Font paths (Ubuntu for GitHub Actions + macOS for local)
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]
FONT_PATH = next((f for f in FONT_PATHS if os.path.exists(f)), "Arial")


def get_font(size, bold=False):
    from PIL import ImageFont
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for f in candidates:
        try:
            return ImageFont.truetype(f, size)
        except Exception:
            continue
    return ImageFont.load_default()


# ══════════════════════════════════════════════════════════════════
#  ASS SUBTITLE GENERATOR (Karaoke + Kinetic Effects)
# ══════════════════════════════════════════════════════════════════

def generate_ass_subtitles(
    script: str,
    audio_duration: float,
    output_path: str,
) -> str:
    """
    Generate ASS subtitles with karaoke word-by-word highlighting
    and CapCut-style bounce/pop effects.

    Uses \\kf tags for progressive color fill (karaoke highlighting).
    Words appear in white, then highlight to cyan as spoken.
    """
    words = script.split()
    if not words:
        return output_path

    # Split into phrases (2-4 words each for readability)
    phrases = []
    chunk_size = random.choice([2, 3, 4])
    for i in range(0, len(words), chunk_size):
        phrases.append(" ".join(words[i:i + chunk_size]))

    # Calculate timing per phrase
    total_words = len(words)
    word_duration = audio_duration / total_words
    current_time = 0.0

    # ASS header
    ass_content = f"""[Script Info]
Title: MindRank Kinetic Captions
ScriptType: v4.00+
PlayResX: {WIDTH}
PlayResY: {HEIGHT}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Karaoke,Arial Black,90,&H00FFFFFF,&H0000D4FF,&H00000000,&H80000000,1,0,0,0,100,100,2,0,1,4,0,5,10,10,120,1
Style: Hook,Arial Black,100,&H0000D4FF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,3,0,1,5,0,5,10,10,100,1
Style: Channel,Arial,50,&H0000D4FF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,8,10,10,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # Add channel name watermark (persistent)
    ass_content += "Dialogue: 1,0:00:00.00,%s,Channel,,0,0,0,,{\\fad(500,500)}MindRank\n" % _format_ass_time(audio_duration)

    # Add karaoke phrases
    for phrase in phrases:
        phrase_words = phrase.split()
        phrase_duration = len(phrase_words) * word_duration
        start_time = current_time
        end_time = current_time + phrase_duration

        # Build karaoke text with \kf tags for progressive fill
        karaoke_parts = []
        for w in phrase_words:
            word_dur_cs = int(word_duration * 100)  # centiseconds
            karaoke_parts.append("{\\kf%d}%s" % (word_dur_cs, w))

        karaoke_text = " ".join(karaoke_parts)

        # Add bounce effect on phrase entry (ASS uses single braces, backslash-escaped)
        bounce_effect = (
            "{\\fscx80\\fscy80}"
            "{\\t(0,150,\\fscx105\\fscy105)}"
            "{\\t(150,300,\\fscx100\\fscy100)}"
        )

        ass_line = (
            f"Dialogue: 0,{_format_ass_time(start_time)},{_format_ass_time(end_time)},"
            f"Karaoke,,0,0,0,,{bounce_effect}{karaoke_text}"
        )
        ass_content += ass_line + "\n"
        current_time = end_time

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    log.info(f"ASS subtitles generated: {output_path}")
    return output_path


def _format_ass_time(seconds: float) -> str:
    """Convert seconds to ASS time format (H:MM:SS.CC)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


# ══════════════════════════════════════════════════════════════════
#  HOOK TEXT GENERATOR (First 3 seconds attention grabber)
# ══════════════════════════════════════════════════════════════════

def generate_hook_frame(
    hook_text: str,
    frame_num: int,
    total_frames: int,
    output_path: str,
):
    """
    Generate a dramatic hook frame for the first 2-3 seconds.
    Large bold text with glow effect on dark background.
    """
    from PIL import Image, ImageDraw, ImageFilter

    img = Image.new("RGB", (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Dark radial gradient background
    for y in range(HEIGHT):
        dist = abs(y - HEIGHT // 2) / (HEIGHT // 2)
        r = int(10 + 15 * (1 - dist))
        g = int(8 + 5 * (1 - dist))
        b = int(20 + 30 * (1 - dist))
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    # Glow circles in background
    for _ in range(3):
        cx = random.randint(WIDTH // 4, 3 * WIDTH // 4)
        cy = random.randint(HEIGHT // 4, 3 * HEIGHT // 4)
        for radius in range(200, 0, -5):
            alpha = int(30 * (1 - radius / 200))
            color = (0, alpha, int(alpha * 1.2))
            draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                        outline=color, width=1)

    # Bold hook text
    font_size = 95
    font = get_font(font_size, bold=True)

    # Word wrap
    words = hook_text.upper().split()
    lines = []
    current_line = []
    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] > WIDTH - 120:
            lines.append(" ".join(current_line))
            current_line = [word]
        else:
            current_line.append(word)
    if current_line:
        lines.append(" ".join(current_line))

    # Draw text with glow
    total_h = len(lines) * (font_size + 20)
    start_y = (HEIGHT - total_h) // 2

    for idx, line in enumerate(lines[:4]):
        bbox = draw.textbbox((0, 0), line, font=font)
        tx = (WIDTH - (bbox[2] - bbox[0])) // 2
        ty = start_y + idx * (font_size + 20)

        # Glow layers
        glow_img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_img)
        glow_draw.text((tx, ty), line, font=font, fill=ACCENT_CYAN)
        glow_img = glow_img.filter(ImageFilter.GaussianBlur(15))
        img = Image.blend(img, glow_img, 0.4)

        draw = ImageDraw.Draw(img)
        # Main text
        draw.text((tx, ty), line, font=font, fill=(255, 255, 255))

    # "SUBSCRIBE" pulse at bottom
    sub_font = get_font(40, bold=True)
    sub_text = "▶ SUBSCRIBE"
    bbox = draw.textbbox((0, 0), sub_text, font=sub_font)
    sx = (WIDTH - (bbox[2] - bbox[0])) // 2
    sy = HEIGHT - 200
    draw.rounded_rectangle([sx - 20, sy - 10, sx + (bbox[2] - bbox[0]) + 20, sy + (bbox[3] - bbox[1]) + 10],
                           radius=16, fill=ACCENT_RED)
    draw.text((sx, sy), sub_text, font=sub_font, fill=(255, 255, 255))

    img.save(output_path, "PNG")
    return output_path


# ══════════════════════════════════════════════════════════════════
#  BACKGROUND VIDEO GENERATOR (Dark animated gradient)
# ══════════════════════════════════════════════════════════════════

def generate_background_video(duration: float, output_path: str) -> str:
    """
    Generate a dark animated background using FFmpeg filters.
    Creates a subtle moving gradient with particle-like effects.
    """
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i",
        f"color=c=0x0A0A0F:s={WIDTH}x{HEIGHT}:d={duration}:r={FPS}",
        "-vf",
        (
            # Animated gradient overlay
            f"drawbox=x=0:y=0:w={WIDTH}:h={HEIGHT}:"
            f"color=0x0D1117@0.3:t=fill,"
            # Subtle moving glow circles
            f"drawtext=text='●':fontsize=200:fontcolor=0x00D4FF@0.05:"
            f"x='mod(t*30,{WIDTH})':y='h/2+100*sin(t*0.5)',"
            f"drawtext=text='●':fontsize=150:fontcolor=0x7B2FBE@0.05:"
            f"x='mod(t*20+400,{WIDTH})':y='h/2+80*cos(t*0.7)',"
            # Vignette effect
            f"vignette=PI/4"
        ),
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        "-pix_fmt", "yuv420p",
        output_path
    ]

    try:
        subprocess.run(cmd, capture_output=True, timeout=120, check=True)
        log.info(f"Background video generated: {output_path}")
        return output_path
    except Exception as e:
        log.warning(f"Background generation failed: {e}")
        return ""


# ══════════════════════════════════════════════════════════════════
#  THUMBNAIL GENERATOR (Clickbait style)
# ══════════════════════════════════════════════════════════════════

def generate_thumbnail(script_data: dict, output_path: str) -> str:
    """Generate a viral clickbait thumbnail: high contrast, bold text."""
    from PIL import Image, ImageDraw, ImageFilter

    thumb_w, thumb_h = 1280, 720
    img = Image.new("RGB", (thumb_w, thumb_h), (10, 10, 15))
    draw = ImageDraw.Draw(img)

    title = script_data.get("title", "SECRET Psychology Trick")

    # Dramatic gradient
    for y in range(thumb_h):
        ratio = y / thumb_h
        r = int(15 + 40 * ratio)
        g = int(5 + 10 * ratio)
        b = int(30 + 50 * (1 - ratio))
        draw.line([(0, y), (thumb_w, y)], fill=(r, g, b))

    # Glow accents
    for _ in range(4):
        cx = random.randint(0, thumb_w)
        cy = random.randint(0, thumb_h)
        for radius in range(150, 0, -3):
            alpha = int(40 * (1 - radius / 150))
            color = random.choice([(0, alpha, int(alpha * 1.2)), (alpha, 0, int(alpha * 0.5))])
            draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                        outline=color, width=1)

    # Bold title
    font = get_font(85, bold=True)
    lines = textwrap.wrap(title.upper(), width=18)
    total_h = len(lines) * 100
    ty = (thumb_h - total_h) // 2

    for line in lines[:3]:
        bbox = draw.textbbox((0, 0), line, font=font)
        tx = (thumb_w - (bbox[2] - bbox[0])) // 2
        # Outline
        for dx in range(-4, 5):
            for dy in range(-4, 5):
                draw.text((tx + dx, ty + dy), line, font=font, fill=(0, 0, 0))
        draw.text((tx, ty), line, font=font, fill=ACCENT_YELLOW)
        ty += 100

    # Subscribe badge
    badge_font = get_font(36, bold=True)
    badge_text = "▶ SUBSCRIBE"
    bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    bx = thumb_w - (bbox[2] - bbox[0]) - 40
    by = thumb_h - (bbox[3] - bbox[1]) - 30
    draw.rounded_rectangle([bx - 16, by - 8, bx + (bbox[2] - bbox[0]) + 16, by + (bbox[3] - bbox[1]) + 8],
                           radius=12, fill=ACCENT_RED)
    draw.text((bx, by), badge_text, font=badge_font, fill=(255, 255, 255))

    # Channel name
    logo_font = get_font(48, bold=True)
    draw.text((30, 30), "MindRank", font=logo_font, fill=ACCENT_CYAN)

    img.save(output_path, "JPEG", quality=95)
    log.info(f"Thumbnail saved: {output_path}")
    return output_path


# ══════════════════════════════════════════════════════════════════
#  MAIN VIDEO GENERATION (FFmpeg composition)
# ══════════════════════════════════════════════════════════════════

def generate_video(script_data: dict, audio_path: str, output_path: str) -> bool:
    """
    Generate a viral YouTube Short using the kinetic typography format:

    1. Generate ASS subtitles with karaoke highlighting
    2. Generate dark animated background
    3. Generate hook frame (first 2-3 seconds)
    4. Composite everything with FFmpeg

    This produces videos that look like actual viral faceless shorts,
    not static images with transitions.
    """
    os.makedirs("output/slides", exist_ok=True)
    os.makedirs("output/thumbnails", exist_ok=True)

    # Get audio duration
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", audio_path],
            capture_output=True, text=True, timeout=10
        )
        duration = float(result.stdout.strip())
    except Exception as e:
        log.error(f"Cannot get audio duration: {e}")
        return False

    log.info(f"Audio duration: {duration:.1f}s")

    script = script_data.get("script", "")
    hook = script_data.get("hook", "")
    title = script_data.get("title", "Amazing Facts")

    # ── Step 1: Generate ASS subtitles ──
    ass_path = "output/subtitles.ass"
    generate_ass_subtitles(script, duration, ass_path)

    # ── Step 2: Generate background video ──
    bg_path = "output/background.mp4"
    generate_background_video(duration, bg_path)

    # ── Step 3: Generate hook frame (first 2.5 seconds) ──
    hook_path = "output/hook_frame.png"
    generate_hook_frame(hook, 0, FPS * 3, hook_path)

    # ── Step 4: Composite with FFmpeg ──
    log.info("Compositing final video with FFmpeg...")

    # Build the FFmpeg command
    if bg_path and os.path.exists(bg_path):
        # Use generated background
        cmd = [
            "ffmpeg", "-y",
            "-i", bg_path,          # Background video
            "-i", audio_path,       # Voiceover
            "-i", hook_path,        # Hook frame (for intro)
            "-filter_complex",
            (
                # Loop hook frame for first 2.5 seconds
                f"[2:v]loop=loop=75:size=1:start=0,"
                f"trim=duration=2.5[hook];"

                # Background starts after hook
                f"[0:v]trim=start=0:end={duration - 2.5},"
                f"setpts=PTS-STARTPTS[bg];"

                # Concat hook + background
                f"[hook][bg]concat=n=2:v=1:a=0[video_base];"

                # Overlay ASS subtitles with karaoke
                f"[video_base]ass={ass_path}[final]"
            ),
            "-map", "[final]",
            "-map", "1:a",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            output_path
        ]
    else:
        # Fallback: solid dark background with ASS subtitles
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i",
            f"color=c=0x0A0A0F:s={WIDTH}x{HEIGHT}:d={duration}:r={FPS}",
            "-i", audio_path,
            "-vf", f"ass={ass_path}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            output_path
        ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            log.error(f"FFmpeg error: {result.stderr[-500:]}")
            # Try simpler fallback
            return _generate_simple_fallback(script_data, audio_path, output_path, duration)
    except Exception as e:
        log.error(f"FFmpeg failed: {e}")
        return _generate_simple_fallback(script_data, audio_path, output_path, duration)

    file_size = os.path.getsize(output_path) / (1024 * 1024)
    log.info(f"Video done: {output_path} ({file_size:.1f} MB)")

    # Generate thumbnail
    thumb_path = output_path.replace(".mp4", "_thumb.jpg").replace("output/", "output/thumbnails/")
    os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
    generate_thumbnail(script_data, thumb_path)

    return True


def _generate_simple_fallback(
    script_data: dict,
    audio_path: str,
    output_path: str,
    duration: float,
) -> bool:
    """
    Simple fallback: dark background + large centered text + audio.
    Uses FFmpeg drawtext for word-by-word appearance.
    """
    log.info("Using simple fallback video generation...")

    script = script_data.get("script", "")
    words = script.split()
    words_per_line = 4
    lines = []
    for i in range(0, len(words), words_per_line):
        lines.append(" ".join(words[i:i + words_per_line]))

    # Build drawtext filter for each line
    word_duration = duration / max(1, len(words))
    drawtext_parts = []
    for i, line in enumerate(lines):
        start_time = i * words_per_line * word_duration
        escaped = line.replace("'", "'\\''").replace(":", "\\:")
        drawtext_parts.append(
            f"drawtext=text='{escaped}':"
            f"fontsize=80:fontcolor=white:"
            f"fontfile={FONT_PATH}:"
            f"x=(w-tw)/2:y=(h-th)/2:"
            f"enable='between(t,{start_time:.2f},{start_time + len(line.split()) * word_duration:.2f})':"
            f"borderw=4:bordercolor=black"
        )

    filter_str = ",".join(drawtext_parts) if drawtext_parts else f"drawtext=text='MindRank':fontsize=60:fontcolor=white:x=(w-tw)/2:y=(h-th)/2"

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i",
        f"color=c=0x0A0A0F:s={WIDTH}x{HEIGHT}:d={duration}:r={FPS}",
        "-i", audio_path,
        "-vf", filter_str,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        output_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            log.error(f"Fallback FFmpeg error: {result.stderr[-300:]}")
            return False
    except Exception as e:
        log.error(f"Fallback failed: {e}")
        return False

    file_size = os.path.getsize(output_path) / (1024 * 1024)
    log.info(f"Fallback video done: {output_path} ({file_size:.1f} MB)")
    return True


# ══════════════════════════════════════════════════════════════════
#  SCENE BUILDER (for compatibility with main.py)
# ══════════════════════════════════════════════════════════════════

def build_scenes_viral(script_data: dict) -> list:
    """Build scenes for compatibility with existing pipeline."""
    script = script_data.get("script", "")
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', script) if len(s.strip()) > 10]
    scenes = []
    for i, sent in enumerate(sentences):
        scenes.append({
            "section": f"Part {i + 1}",
            "narration": sent,
            "image_prompt": f"dramatic dark {sent[:40]}",
            "style": "dark",
        })
    return scenes


# ══════════════════════════════════════════════════════════════════
#  AI IMAGE GENERATOR (kept for compatibility)
# ══════════════════════════════════════════════════════════════════

def generate_ai_image_cinematic(scene_description: str, style: str = "cinematic"):
    """Kept for compatibility. Not used in kinetic typography mode."""
    return None


def create_dramatic_fallback(scene_num: int, narration: str, title: str):
    """Kept for compatibility."""
    from PIL import Image
    return Image.new("RGB", (WIDTH, HEIGHT), BG_DARK)


def compose_frame_viral(*args, **kwargs):
    """Kept for compatibility."""
    from PIL import Image
    return Image.new("RGB", (WIDTH, HEIGHT), BG_DARK)
