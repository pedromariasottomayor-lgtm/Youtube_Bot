"""
Viral YouTube Shorts Generator — Professional Stock Footage + Karaoke Captions
Uses Pexels stock footage backgrounds + ASS karaoke subtitles.
This is what top viral faceless channels actually use.
"""

import os
import re
import math
import time
import textwrap
import random
import logging
import subprocess
from typing import List, Tuple, Optional

log = logging.getLogger(__name__)

WIDTH  = 1080
HEIGHT = 1920
FPS    = 30

ACCENT_CYAN   = (0, 212, 255)
ACCENT_YELLOW = (255, 220, 0)
ACCENT_RED    = (255, 50, 50)
ACCENT_GREEN  = (80, 220, 120)


def get_font(size, bold=False):
    from PIL import ImageFont
    if bold:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    for f in candidates:
        try:
            return ImageFont.truetype(f, size)
        except Exception:
            continue
    return ImageFont.load_default()


# ══════════════════════════════════════════════════════════════════
#  ASS KARAOKE SUBTITLE GENERATOR (CapCut Professional Style)
# ══════════════════════════════════════════════════════════════════

def _format_ass_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def generate_ass_subtitles(script: str, audio_duration: float, output_path: str) -> str:
    """
    Generate professional ASS subtitles with CapCut-style effects.
    - Word-by-word karaoke highlighting (\kf)
    - Bounce/pop animation on phrase entry
    - Glow outline (cyan/purple)
    - Text shadow for depth
    - Persistent channel watermark
    """
    words = script.split()
    phrases = []
    current = []
    for w in words:
        current.append(w)
        if len(current) >= random.randint(2, 4) or w.endswith(('.', '!', '?')):
            phrases.append(' '.join(current))
            current = []
    if current:
        phrases.append(' '.join(current))

    n_phrases = len(phrases)
    phrase_duration = audio_duration / n_phrases if n_phrases > 0 else audio_duration

    ass_content = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Karaoke,Arial,78,&H00FFFFFF,&H0000D4FF,&H00000000,&H96000000,-1,0,0,0,100,100,3,0,1,5,3,5,60,60,140,1
Style: Glow,Arial,78,&H00D4FFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,3,0,1,8,0,5,60,60,140,1
Style: Channel,Arial,32,&H00D4FFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,7,60,60,30,1
Style: BigWord,Arial,100,&H0000D4FF,&H00FFFFFF,&H00000000,&HA0000000,-1,0,0,0,100,100,5,0,1,6,3,5,60,60,160,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    for i, phrase in enumerate(phrases):
        start_time = i * phrase_duration
        end_time = min((i + 1) * phrase_duration, audio_duration)
        phrase_words = phrase.split()
        word_duration = (end_time - start_time) / len(phrase_words) if phrase_words else 0.1

        # Build karaoke text with \kf tags
        karaoke_parts = []
        for w in phrase_words:
            word_dur_cs = int(word_duration * 100)
            karaoke_parts.append("{\\kf%d}%s" % (word_dur_cs, w))
        karaoke_text = " ".join(karaoke_parts)

        # Bounce effect on entry (scale from 80% to 105% to 100%)
        bounce = (
            "{\\fscx80\\fscy80}"
            "{\\t(0,120,\\fscx108\\fscy108)}"
            "{\\t(120,250,\\fscx100\\fscy100)}"
        )

        # Glow layer (behind main text, slightly larger, colored)
        glow_text = "{\\kf0}".join(["%s" % w for w in phrase_words])

        start_str = _format_ass_time(start_time)
        end_str = _format_ass_time(end_time)

        # Main karaoke line (white text, cyan highlight)
        ass_content += f"Dialogue: 0,{start_str},{end_str},Karaoke,,0,0,0,,{bounce}{karaoke_text}\n"

        # Glow layer (cyan, slightly offset, behind)
        ass_content += f"Dialogue: -1,{start_str},{end_str},Glow,,0,0,0,,{bounce}{glow_text}\n"

    # Channel watermark
    ass_content += "Dialogue: 1,0:00:00.00,%s,Channel,,0,0,0,,{\\fad(800,800)}{\\pos(540,1850)}🧠 MindRank\n" % _format_ass_time(audio_duration)

    # Occasional big emphasis words (every ~5 seconds)
    emphasis_words = ["NEVER", "ALWAYS", "SECRET", "TRUTH", "DANGER", "POWER", "MIND", "BRAIN"]
    for t_sec in range(3, int(audio_duration), 5):
        word = random.choice(emphasis_words)
        t_start = _format_ass_time(t_sec)
        t_end = _format_ass_time(min(t_sec + 1.5, audio_duration))
        ass_content += f"Dialogue: 2,{t_start},{t_end},BigWord,,0,0,0,,{{\\fad(200,300)}}{{\\pos(540,960)}}{word}\n"

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    log.info(f"ASS subtitles generated: {output_path}")
    return output_path


# ══════════════════════════════════════════════════════════════════
#  THUMBNAIL GENERATOR (Maximum Clickbait)
# ══════════════════════════════════════════════════════════════════

def generate_thumbnail(script_data: dict, output_path: str) -> str:
    """Generate maximum-impact clickbait thumbnail."""
    from PIL import Image, ImageDraw, ImageFilter

    thumb_w, thumb_h = 1280, 720
    img = Image.new("RGB", (thumb_w, thumb_h), (5, 5, 12))
    draw = ImageDraw.Draw(img)

    title = script_data.get("title", "THE SECRET NOBODY TELLS YOU")

    # Dramatic gradient background
    for y in range(thumb_h):
        ratio = y / thumb_h
        r = int(10 + 30 * math.sin(ratio * 3))
        g = int(3 + 8 * ratio)
        b = int(20 + 45 * (1 - ratio))
        draw.line([(0, y), (thumb_w, y)], fill=(r, g, b))

    # Big glowing orbs
    for _ in range(6):
        cx = random.randint(0, thumb_w)
        cy = random.randint(0, thumb_h)
        radius = random.randint(80, 180)
        color = random.choice([ACCENT_CYAN, (123, 47, 187)])
        r, g, b = color
        for i in range(radius, 0, -3):
            alpha_factor = (1 - i / radius) ** 1.5
            a = int(45 * alpha_factor)
            if a < 1:
                continue
            draw.ellipse([cx - i, cy - i, cx + i, cy + i], fill=(r, g, b))

    # BIG title text with glow
    font = get_font(100, bold=True)
    lines = textwrap.wrap(title.upper(), width=14)
    total_h = len(lines) * 115
    ty = (thumb_h - total_h) // 2

    for line in lines[:3]:
        bbox = draw.textbbox((0, 0), line, font=font)
        tx = (thumb_w - (bbox[2] - bbox[0])) // 2

        # Glow behind text
        glow_img = Image.new("RGB", (thumb_w, thumb_h), (0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_img)
        glow_draw.text((tx, ty), line, font=font, fill=ACCENT_YELLOW)
        glow_img = glow_img.filter(ImageFilter.GaussianBlur(12))
        img = Image.blend(img, glow_img, 0.4)
        draw = ImageDraw.Draw(img)

        # Thick outline
        for dx in range(-5, 6):
            for dy in range(-5, 6):
                draw.text((tx + dx, ty + dy), line, font=font, fill=(0, 0, 0))

        # Main text
        draw.text((tx, ty), line, font=font, fill=ACCENT_YELLOW)
        ty += 115

    # Subscribe badge
    badge_font = get_font(44, bold=True)
    badge_text = "SUBSCRIBE"
    bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    bw = bbox[2] - bbox[0]
    bh = bbox[3] - bbox[1]
    bx = thumb_w - bw - 50
    by = thumb_h - bh - 40
    draw.rounded_rectangle([bx - 22, by - 14, bx + bw + 22, by + bh + 14],
                           radius=16, fill=ACCENT_RED)
    draw.text((bx, by), badge_text, font=badge_font, fill=(255, 255, 255))

    # Channel name
    logo_font = get_font(56, bold=True)
    logo_glow = Image.new("RGB", (thumb_w, thumb_h), (0, 0, 0))
    logo_glow_draw = ImageDraw.Draw(logo_glow)
    logo_glow_draw.text((30, 25), "MindRank", font=logo_font, fill=ACCENT_CYAN)
    logo_glow = logo_glow.filter(ImageFilter.GaussianBlur(8))
    img = Image.blend(img, logo_glow, 0.3)
    draw = ImageDraw.Draw(img)
    draw.text((30, 25), "MindRank", font=logo_font, fill=ACCENT_CYAN)

    # Emoji/icon accent
    try:
        emoji_font = get_font(80)
        draw.text((thumb_w - 120, 20), "🧠", font=emoji_font, fill=(255, 255, 255))
    except Exception:
        pass

    img.save(output_path, "JPEG", quality=95)
    log.info(f"Thumbnail saved: {output_path}")
    return output_path


# ══════════════════════════════════════════════════════════════════
#  MAIN VIDEO COMPOSITION
# ══════════════════════════════════════════════════════════════════

def generate_video(script_data: dict, audio_path: str, output_dir: str) -> str:
    """
    Generate viral short video:
    1. Download stock footage from Pexels (free, vertical)
    2. Add ASS karaoke subtitles (CapCut style)
    3. Add audio
    4. Upload to YouTube
    """
    from scripts.stock_footage import get_stock_for_script, concatenate_clips

    # Handle both file path and directory path
    if output_dir.endswith(".mp4"):
        video_path = output_dir
        work_dir = os.path.dirname(video_path) or "."
    else:
        work_dir = output_dir
        os.makedirs(work_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        video_path = os.path.join(work_dir, f"video_{timestamp}.mp4")

    os.makedirs(work_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(video_path))[0]

    thumb_dir = os.path.join(work_dir, "thumbnails")
    os.makedirs(thumb_dir, exist_ok=True)
    thumb_path = os.path.join(thumb_dir, f"{base}_thumb.jpg")

    # Get audio duration
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            capture_output=True, text=True, timeout=10
        )
        audio_duration = float(probe.stdout.strip())
    except Exception:
        audio_duration = 25.0

    log.info(f"Audio duration: {audio_duration:.1f}s")

    # Step 1: Get stock footage
    script_text = script_data.get("script", "")
    stock_clips = get_stock_for_script(script_text, work_dir, audio_duration)

    # Step 2: Create background video from stock footage
    bg_path = os.path.join(work_dir, f"{base}_bg.mp4")

    if stock_clips and len(stock_clips) >= 2:
        log.info(f"Compositing {len(stock_clips)} stock clips...")
        success = concatenate_clips(stock_clips, bg_path, audio_duration + 1)
        if not success:
            stock_clips = []
    
    if not stock_clips:
        log.info("No stock footage available, using animated gradient fallback")
        _generate_fallback_bg(bg_path, audio_duration + 1)

    # Step 3: Generate ASS subtitles
    ass_path = os.path.join(work_dir, f"{base}.ass")
    generate_ass_subtitles(script_text, audio_duration, ass_path)

    # Step 4: Composite everything with FFmpeg
    log.info("Compositing final video...")

    # Apply darkening overlay + vignette + subtitles
    filter_complex = (
        # Darken stock footage slightly for readability
        f"[0:v]eq=brightness=-0.08:contrast=1.1,"
        # Vignette for cinematic look
        f"vignette=PI/4.5,"
        # Burn ASS subtitles
        f"ass={ass_path}"
        f"[final]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", bg_path,
        "-i", audio_path,
        "-filter_complex", filter_complex,
        "-map", "[final]",
        "-map", "1:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        "-movflags", "+faststart",
        video_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)

    if result.returncode == 0:
        size_mb = os.path.getsize(video_path) / (1024 * 1024)
        log.info(f"Video done: {video_path} ({size_mb:.1f} MB)")
    else:
        log.error(f"FFmpeg failed: {result.stderr[:500]}")
        # Try simpler fallback
        cmd_simple = [
            "ffmpeg", "-y",
            "-i", bg_path,
            "-i", audio_path,
            "-filter_complex",
            f"[0:v]vignette=PI/4,ass={ass_path}[final]",
            "-map", "[final]", "-map", "1:a",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            "-movflags", "+faststart",
            video_path
        ]
        result2 = subprocess.run(cmd_simple, capture_output=True, text=True, timeout=180)
        if result2.returncode != 0:
            log.error(f"Fallback failed: {result2.stderr[:300]}")
            return ""
        size_mb = os.path.getsize(video_path) / (1024 * 1024)
        log.info(f"Video done (fallback): {video_path} ({size_mb:.1f} MB)")

    # Step 5: Generate thumbnail
    generate_thumbnail(script_data, thumb_path)
    script_data["thumbnail_path"] = thumb_path

    # Cleanup
    for f in [bg_path] + stock_clips:
        try:
            if f != video_path:
                os.remove(f)
        except OSError:
            pass

    return video_path


def _generate_fallback_bg(output_path: str, duration: float):
    """Generate fallback animated gradient background."""
    from PIL import Image

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i",
        f"color=c=0x0A0A12:s={WIDTH}x{HEIGHT}:d={duration}:r={FPS}",
        "-vf", (
            f"drawtext=text='●':fontsize=180:fontcolor=0x00D4FF@0.04:"
            f"x='mod(t*25,{WIDTH})':y='h/2+80*sin(t*0.4)',"
            f"drawtext=text='●':fontsize=140:fontcolor=0x7B2FBE@0.04:"
            f"x='mod(t*18+300,{WIDTH})':y='h/2+60*cos(t*0.6)',"
            f"vignette=PI/4"
        ),
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        "-pix_fmt", "yuv420p",
        output_path
    ]

    try:
        subprocess.run(cmd, capture_output=True, timeout=60, check=True)
    except Exception as e:
        log.warning(f"Fallback bg failed: {e}")
