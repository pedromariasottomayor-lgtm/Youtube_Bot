"""
Viral YouTube Shorts Generator — Real Animation Style
Uses Pillow frame-by-frame rendering → FFmpeg pipe for animated backgrounds.
ASS karaoke subtitles for CapCut-style word-by-word captions.
"""

import os
import re
import math
import time
import textwrap
import random
import logging
import subprocess
import struct
import zlib
from typing import List, Tuple, Optional
from io import BytesIO

log = logging.getLogger(__name__)

WIDTH  = 1080
HEIGHT = 1920
FPS    = 15  # 15fps for speed on GitHub Actions

ACCENT_CYAN   = (0, 212, 255)
ACCENT_PURPLE = (123, 47, 187)
ACCENT_YELLOW = (255, 220, 0)
ACCENT_RED    = (255, 50, 50)
BG_DARK       = (10, 10, 18)
BG_MID        = (15, 12, 30)


# ══════════════════════════════════════════════════════════════════
#  FONT HELPERS
# ══════════════════════════════════════════════════════════════════

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
#  PARTICLE SYSTEM (pure math, no pygame needed)
# ══════════════════════════════════════════════════════════════════

class Particle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'size', 'color', 'alpha', 'life', 'max_life', 'wobble_amp', 'wobble_freq')

    def __init__(self, w, h, color=None):
        self.x = random.uniform(0, w)
        self.y = random.uniform(h * 0.3, h * 1.2)
        self.vx = random.uniform(-0.3, 0.3)
        self.vy = random.uniform(-1.5, -0.5)
        self.size = random.uniform(1.5, 4.0)
        self.color = color or random.choice([ACCENT_CYAN, ACCENT_PURPLE, (255, 255, 255)])
        self.alpha = random.uniform(0.3, 0.8)
        self.life = 0.0
        self.max_life = random.uniform(4.0, 10.0)
        self.wobble_amp = random.uniform(10, 40)
        self.wobble_freq = random.uniform(0.5, 2.0)

    def update(self, dt):
        self.life += dt
        self.x += self.vx * dt * 60 + math.sin(self.life * self.wobble_freq) * self.wobble_amp * dt
        self.y += self.vy * dt * 60
        # Fade in/out
        progress = self.life / self.max_life
        if progress < 0.1:
            self.alpha = min(0.8, progress / 0.1 * 0.8)
        elif progress > 0.7:
            self.alpha = max(0, (1 - progress) / 0.3 * 0.8)
        else:
            self.alpha = 0.8

    def alive(self):
        return self.life < self.max_life and self.y > -50


class GlowOrb:
    __slots__ = ('x', 'y', 'vx', 'vy', 'base_radius', 'color', 'phase', 'speed')

    def __init__(self, w, h):
        self.x = random.uniform(w * 0.1, w * 0.9)
        self.y = random.uniform(h * 0.2, h * 0.8)
        self.vx = random.uniform(-0.5, 0.5)
        self.vy = random.uniform(-0.3, 0.3)
        self.base_radius = random.uniform(60, 120)
        self.color = random.choice([ACCENT_CYAN, ACCENT_PURPLE])
        self.phase = random.uniform(0, 2 * math.pi)
        self.speed = random.uniform(0.3, 0.8)

    def update(self, dt, t):
        self.x += self.vx * dt * 30
        self.y += self.vy * dt * 30
        # Gentle pulsing
        pulse = 1.0 + 0.3 * math.sin(t * self.speed + self.phase)
        return int(self.base_radius * pulse)

    def draw(self, img, t):
        from PIL import ImageDraw
        radius = self.update(1.0 / FPS, t)
        draw = ImageDraw.Draw(img)
        r, g, b = self.color
        # Draw concentric circles for glow
        for i in range(radius, 0, -2):
            alpha_factor = (1 - i / radius) ** 2
            a = int(25 * alpha_factor)
            if a < 1:
                continue
            # Blend: manual pixel-level glow
            cx, cy = int(self.x), int(self.y)
            x0, y0 = max(0, cx - i), max(0, cy - i)
            x1, y1 = min(WIDTH, cx + i), min(HEIGHT, cy + i)
            if x1 > x0 and y1 > y0:
                draw.ellipse([x0, y0, x1, y1], fill=(r, g, b, a))


# ══════════════════════════════════════════════════════════════════
#  BACKGROUND FRAME GENERATOR (Pillow-based)
# ══════════════════════════════════════════════════════════════════

def _draw_gradient_bg(img, t):
    """Draw animated dark gradient with subtle color shift."""
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    shift = math.sin(t * 0.3) * 10
    for y in range(0, HEIGHT, 4):
        ratio = y / HEIGHT
        r = int(BG_DARK[0] + (BG_MID[0] - BG_DARK[0]) * ratio + shift * ratio)
        g = int(BG_DARK[1] + (BG_MID[1] - BG_DARK[1]) * ratio)
        b = int(BG_DARK[2] + (BG_MID[2] - BG_DARK[2]) * ratio - shift * 0.5 * ratio)
        r, g, b = max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))
        draw.rectangle([(0, y), (WIDTH, y + 4)], fill=(r, g, b))


def _draw_vignette(img):
    """Draw vignette (dark edges)."""
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    cx, cy = WIDTH // 2, HEIGHT // 2
    max_dist = math.sqrt(cx ** 2 + cy ** 2)
    # Approximate vignette with concentric rectangles
    for i in range(20):
        frac = i / 20
        inset = int(frac * min(WIDTH, HEIGHT) * 0.4)
        alpha = int(80 * frac ** 2)
        if alpha < 1:
            continue
        x0, y0 = inset, inset
        x1, y1 = WIDTH - inset, HEIGHT - inset
        # Draw semi-transparent dark border
        for edge_inset in range(max(0, inset - 3), inset + 3):
            a = int(alpha * (1 - abs(edge_inset - inset) / 3))
            if a < 1:
                continue
            draw.rectangle(
                [edge_inset, edge_inset, WIDTH - edge_inset, HEIGHT - edge_inset],
                outline=(0, 0, 0, a)
            )
        break


def _draw_particles_on_frame(img, particles, orbs, t):
    """Draw all particles and orbs onto the frame."""
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)

    # Draw glow orbs first (background layer)
    for orb in orbs:
        radius = orb.update(1.0 / FPS, t)
        r, g, b = orb.color
        cx, cy = int(orb.x), int(orb.y)
        # Soft glow layers
        for i in range(radius, 0, -4):
            alpha_factor = (1 - i / radius) ** 1.5
            a = int(30 * alpha_factor)
            if a < 1:
                continue
            x0, y0 = max(0, cx - i), max(0, cy - i)
            x1, y1 = min(WIDTH, cx + i), min(HEIGHT, cy + i)
            if x1 > x0 and y1 > y0:
                draw.ellipse([x0, y0, x1, y1], fill=(r, g, b, a))

    # Draw particles
    for p in particles:
        if not p.alive():
            continue
        r, g, b = p.color
        a = int(p.alpha * 255)
        if a < 1:
            continue
        cx, cy = int(p.x), int(p.y)
        sz = max(1, int(p.size))
        x0, y0 = max(0, cx - sz), max(0, cy - sz)
        x1, y1 = min(WIDTH, cx + sz), min(HEIGHT, cy + sz)
        if x1 > x0 and y1 > y0:
            draw.ellipse([x0, y0, x1, y1], fill=(r, g, b, a))


def _draw_scanlines(img, intensity=0.03):
    """Subtle scanlines for cinematic look."""
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    for y in range(0, HEIGHT, 3):
        draw.line([(0, y), (WIDTH, y)], fill=(0, 0, 0, int(255 * intensity)))


def generate_background_video(duration: float, output_path: str) -> str:
    """
    Generate animated background using Pillow frames piped to FFmpeg.
    Creates floating particles, glowing orbs, and animated gradients.
    """
    from PIL import Image

    log.info("Generating animated background (Pillow → FFmpeg pipe)...")

    # Initialize particles and orbs
    n_particles = 80
    n_orbs = 5
    particles = [Particle(WIDTH, HEIGHT) for _ in range(n_particles)]
    orbs = [GlowOrb(WIDTH, HEIGHT) for _ in range(n_orbs)]

    total_frames = int(duration * FPS)

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgba",
        "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS),
        "-i", "pipe:0",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
        "-pix_fmt", "yuv420p",
        output_path
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        for frame_idx in range(total_frames):
            t = frame_idx / FPS

            # Create RGBA frame
            img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))

            # 1. Animated gradient background
            _draw_gradient_bg(img, t)

            # 2. Update and draw particles
            for p in particles:
                p.update(1.0 / FPS)
                if not p.alive():
                    # Respawn
                    particles[particles.index(p)] = Particle(WIDTH, HEIGHT)

            # 3. Draw orbs (gentle pulsing glow)
            _draw_particles_on_frame(img, particles, orbs, t)

            # 4. Subtle scanlines
            _draw_scanlines(img, 0.02)

            # 5. Vignette (dark edges)
            _draw_vignette(img)

            # Convert RGBA → RGB for FFmpeg
            rgb_img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
            rgb_img.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)

            # Write raw RGB to FFmpeg stdin
            proc.stdin.write(rgb_img.tobytes())

            if frame_idx % (FPS * 2) == 0:
                log.info(f"  Background: {frame_idx}/{total_frames} frames ({int(t)}s)")

        proc.stdin.close()
        proc.wait(timeout=60)

        if proc.returncode == 0:
            log.info(f"Background video generated: {output_path}")
            return output_path
        else:
            err = proc.stderr.read().decode() if proc.stderr else "Unknown error"
            log.warning(f"FFmpeg background failed: {err[:200]}")
            return ""
    except Exception as e:
        log.warning(f"Background generation failed: {e}")
        proc.kill()
        return ""


# ══════════════════════════════════════════════════════════════════
#  ASS KARAOKE SUBTITLE GENERATOR
# ══════════════════════════════════════════════════════════════════

def _format_ass_time(seconds):
    """Format seconds to ASS time (H:MM:SS.cc)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def generate_ass_subtitles(script: str, audio_duration: float, output_path: str) -> str:
    """
    Generate ASS subtitles with CapCut-style karaoke effects.
    - Word-by-word highlighting (\kf tags)
    - Bounce/pop animation on each phrase
    - Glow outline on text
    - Persistent channel name watermark
    """
    # Split script into short phrases (2-5 words each)
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

    # ASS header
    ass_content = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Karaoke,Arial,80,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,4,2,5,60,60,120,1
Style: Channel,Arial,36,&H00D4FFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,7,60,60,30,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    for i, phrase in enumerate(phrases):
        start_time = i * phrase_duration
        end_time = min((i + 1) * phrase_duration, audio_duration)
        phrase_words = phrase.split()
        word_duration = (end_time - start_time) / len(phrase_words) if phrase_words else 0.1

        # Build karaoke text with \kf tags for progressive fill
        karaoke_parts = []
        for w in phrase_words:
            word_dur_cs = int(word_duration * 100)  # centiseconds
            karaoke_parts.append("{\\kf%d}%s" % (word_dur_cs, w))

        karaoke_text = " ".join(karaoke_parts)

        # Bounce effect on phrase entry (ASS uses single braces, backslash-escaped)
        bounce_effect = (
            "{\\fscx80\\fscy80}"
            "{\\t(0,150,\\fscx105\\fscy105)}"
            "{\\t(150,300,\\fscx100\\fscy100)}"
        )

        # Glow outline effect
        glow_effect = "{\\4c&H00D4FF&\\4a&H40&}"

        # Combine: glow + bounce + karaoke text
        dialogue_text = glow_effect + bounce_effect + karaoke_text

        start_str = _format_ass_time(start_time)
        end_str = _format_ass_time(end_time)

        ass_content += f"Dialogue: 0,{start_str},{end_str},Karaoke,,0,0,0,,{dialogue_text}\n"

    # Add channel name watermark (persistent)
    ass_content += "Dialogue: 1,0:00:00.00,%s,Channel,,0,0,0,,{\\fad(500,500)}MindRank\n" % _format_ass_time(audio_duration)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    log.info(f"ASS subtitles generated: {output_path}")
    return output_path


# ══════════════════════════════════════════════════════════════════
#  HOOK FRAME GENERATOR (First 2-3 seconds eye-catching)
# ══════════════════════════════════════════════════════════════════

def generate_hook_frame(title: str, output_path: str) -> str:
    """Generate an eye-catching hook frame for the first 2-3 seconds."""
    from PIL import Image, ImageDraw, ImageFilter

    img = Image.new("RGB", (WIDTH, HEIGHT), (5, 5, 12))
    draw = ImageDraw.Draw(img)

    # Animated gradient
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(8 + 25 * math.sin(ratio * 3))
        g = int(5 + 15 * ratio)
        b = int(20 + 40 * (1 - ratio))
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    # Glowing accent circles
    for _ in range(6):
        cx = random.randint(100, WIDTH - 100)
        cy = random.randint(200, HEIGHT - 200)
        radius = random.randint(80, 160)
        color = random.choice([ACCENT_CYAN, ACCENT_PURPLE])
        r, g, b = color
        for i in range(radius, 0, -3):
            alpha = int(35 * (1 - i / radius) ** 2)
            if alpha < 1:
                continue
            draw.ellipse([cx - i, cy - i, cx + i, cy + i], fill=(r, g, b))

    # Big impact title
    font = get_font(90, bold=True)
    title_upper = title.upper()
    lines = textwrap.wrap(title_upper, width=16)
    total_h = len(lines) * 105
    ty = (HEIGHT - total_h) // 2

    for line in lines[:4]:
        bbox = draw.textbbox((0, 0), line, font=font)
        tx = (WIDTH - (bbox[2] - bbox[0])) // 2
        # Glow
        glow_img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_img)
        glow_draw.text((tx, ty), line, font=font, fill=ACCENT_CYAN)
        glow_img = glow_img.filter(ImageFilter.GaussianBlur(15))
        img = Image.blend(img, glow_img, 0.4)
        draw = ImageDraw.Draw(img)
        # Outline
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                draw.text((tx + dx, ty + dy), line, font=font, fill=(0, 0, 0))
        draw.text((tx, ty), line, font=font, fill=(255, 255, 255))
        ty += 105

    img.save(output_path, "PNG")
    log.info(f"Hook frame saved: {output_path}")
    return output_path


# ══════════════════════════════════════════════════════════════════
#  THUMBNAIL GENERATOR (Clickbait style)
# ══════════════════════════════════════════════════════════════════

def generate_thumbnail(script_data: dict, output_path: str) -> str:
    """Generate a viral clickbait thumbnail: high contrast, bold text, dramatic."""
    from PIL import Image, ImageDraw, ImageFilter

    thumb_w, thumb_h = 1280, 720
    img = Image.new("RGB", (thumb_w, thumb_h), (10, 10, 15))
    draw = ImageDraw.Draw(img)

    title = script_data.get("title", "SECRET Psychology Trick")

    # Dramatic gradient background
    for y in range(thumb_h):
        ratio = y / thumb_h
        r = int(12 + 35 * math.sin(ratio * 2.5))
        g = int(5 + 8 * ratio)
        b = int(25 + 50 * (1 - ratio))
        draw.line([(0, y), (thumb_w, y)], fill=(r, g, b))

    # Big glowing orbs
    for _ in range(5):
        cx = random.randint(0, thumb_w)
        cy = random.randint(0, thumb_h)
        radius = random.randint(100, 200)
        color = random.choice([ACCENT_CYAN, ACCENT_PURPLE])
        r, g, b = color
        for i in range(radius, 0, -3):
            alpha_factor = (1 - i / radius) ** 1.5
            a = int(50 * alpha_factor)
            if a < 1:
                continue
            draw.ellipse([cx - i, cy - i, cx + i, cy + i], fill=(r, g, b))

    # Title text - BIG and impactful
    font = get_font(95, bold=True)
    lines = textwrap.wrap(title.upper(), width=16)
    total_h = len(lines) * 110
    ty = (thumb_h - total_h) // 2

    for line in lines[:3]:
        bbox = draw.textbbox((0, 0), line, font=font)
        tx = (thumb_w - (bbox[2] - bbox[0])) // 2
        # Thick outline
        for dx in range(-5, 6):
            for dy in range(-5, 6):
                draw.text((tx + dx, ty + dy), line, font=font, fill=(0, 0, 0))
        # Main text with glow
        glow_img = Image.new("RGB", (thumb_w, thumb_h), (0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_img)
        glow_draw.text((tx, ty), line, font=font, fill=ACCENT_YELLOW)
        glow_img = glow_img.filter(ImageFilter.GaussianBlur(8))
        img = Image.blend(img, glow_img, 0.3)
        draw = ImageDraw.Draw(img)
        draw.text((tx, ty), line, font=font, fill=ACCENT_YELLOW)
        ty += 110

    # Subscribe badge - bigger
    badge_font = get_font(42, bold=True)
    badge_text = "▶ SUBSCRIBE"
    bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    bw = bbox[2] - bbox[0]
    bh = bbox[3] - bbox[1]
    bx = thumb_w - bw - 50
    by = thumb_h - bh - 40
    draw.rounded_rectangle(
        [bx - 20, by - 12, bx + bw + 20, by + bh + 12],
        radius=14, fill=ACCENT_RED
    )
    draw.text((bx, by), badge_text, font=badge_font, fill=(255, 255, 255))

    # Channel name
    logo_font = get_font(52, bold=True)
    # Glow behind logo
    logo_glow = Image.new("RGB", (thumb_w, thumb_h), (0, 0, 0))
    logo_glow_draw = ImageDraw.Draw(logo_glow)
    logo_glow_draw.text((30, 30), "MindRank", font=logo_font, fill=ACCENT_CYAN)
    logo_glow = logo_glow.filter(ImageFilter.GaussianBlur(6))
    img = Image.blend(img, logo_glow, 0.3)
    draw = ImageDraw.Draw(img)
    draw.text((30, 30), "MindRank", font=logo_font, fill=ACCENT_CYAN)

    img.save(output_path, "JPEG", quality=95)
    log.info(f"Thumbnail saved: {output_path}")
    return output_path


# ══════════════════════════════════════════════════════════════════
#  MAIN VIDEO COMPOSITION
# ══════════════════════════════════════════════════════════════════

def generate_video(script_data: dict, audio_path: str, output_dir: str) -> str:
    """
    Generate a complete viral short video:
    1. Animated background (Pillow particles + FFmpeg)
    2. Hook frame for first 2-3 seconds
    3. ASS karaoke subtitles
    4. Composite everything with FFmpeg

    output_dir can be either a directory path or a full video file path.
    """
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

    # Step 1: Generate animated background
    bg_path = os.path.join(work_dir, f"{base}_bg.mp4")
    bg_result = generate_background_video(audio_duration + 2, bg_path)

    if not bg_result:
        log.warning("Background generation failed, using solid color fallback")
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i",
            f"color=c=0x0A0A0F:s={WIDTH}x{HEIGHT}:d={audio_duration + 2}:r={FPS}",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-pix_fmt", "yuv420p", bg_path
        ], capture_output=True, timeout=60)
        bg_result = bg_path

    # Step 2: Generate hook frame overlay
    hook_path = os.path.join(work_dir, f"{base}_hook.png")
    title = script_data.get("title", "DID YOU KNOW?")
    generate_hook_frame(title, hook_path)

    # Step 3: Generate ASS subtitles
    ass_path = os.path.join(work_dir, f"{base}.ass")
    generate_ass_subtitles(
        script_data.get("script", ""),
        audio_duration,
        ass_path
    )

    # Step 4: Composite everything with FFmpeg
    log.info("Compositing final video with FFmpeg...")

    # Build FFmpeg filter complex
    # [0:v] = background video
    # [1:v] = hook frame image (shown for first 2.5 seconds)
    # [2:a] = audio
    # ass subtitles burned on top
    filter_complex = (
        # Show hook frame for first 2.5s with fade out
        f"[1:v]scale={WIDTH}:{HEIGHT},"
        f"format=rgba,"
        f"fade=t=in:st=0:d=0.5,"
        f"fade=t=out:st=2.0:d=1.0"
        f"[hook];"
        # Overlay hook on background (visible for ~3 seconds)
        f"[0:v][hook]overlay=0:0:enable='between(t,0,3)'[bg_hook];"
        # Add vignette for cinematic look
        f"[bg_hook]vignette=PI/5[vignetted];"
        # Burn ASS subtitles
        f"[vignetted]ass={ass_path}[final]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", bg_result,       # background video
        "-i", hook_path,        # hook frame
        "-i", audio_path,       # audio
        "-filter_complex", filter_complex,
        "-map", "[final]",
        "-map", "2:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
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
        log.error(f"FFmpeg composite failed: {result.stderr[:500]}")
        # Fallback: simple composite without hook frame
        log.info("Trying fallback: simple background + audio + subtitles")
        cmd_simple = [
            "ffmpeg", "-y",
            "-i", bg_result,
            "-i", audio_path,
            "-filter_complex",
            f"[0:v]vignette=PI/5,ass={ass_path}[final]",
            "-map", "[final]", "-map", "1:a",
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            "-movflags", "+faststart",
            video_path
        ]
        result2 = subprocess.run(cmd_simple, capture_output=True, text=True, timeout=180)
        if result2.returncode != 0:
            log.error(f"Fallback also failed: {result2.stderr[:300]}")
            return ""
        size_mb = os.path.getsize(video_path) / (1024 * 1024)
        log.info(f"Video done (fallback): {video_path} ({size_mb:.1f} MB)")

    # Step 5: Generate thumbnail
    generate_thumbnail(script_data, thumb_path)

    # Cleanup temp files
    for f in [bg_path, hook_path]:
        try:
            os.remove(f)
        except OSError:
            pass

    return video_path
