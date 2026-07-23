"""
Step 3: Generate viral YouTube Shorts video
- Cinematic AI images with dramatic prompts
- Zoom/pan motion effects (Ken Burns) on every scene
- Bold animated text overlays (word-by-word reveal)
- Crossfade transitions between scenes
- Dramatic thumbnail generation
- 20-35 second optimal runtime
"""

import os
import re
import math
import time
import random
import textwrap
import logging
import urllib.request
import urllib.parse
import subprocess
from typing import Optional, List, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from io import BytesIO

log = logging.getLogger(__name__)

# ── Viral Shorts dimensions ──
WIDTH  = 1080
HEIGHT = 1920
FPS    = 30

# ── Brand colors (viral-friendly high contrast) ──
CHANNEL_NAME  = "MindRank"
ACCENT_CYAN   = (0, 212, 255)
ACCENT_RED    = (255, 50, 50)
ACCENT_YELLOW = (255, 220, 0)
BG_DARK       = (10, 10, 15)
TEXT_WHITE     = (255, 255, 255)
TEXT_SHADOW    = (0, 0, 0)

# ── Safe zone (avoid YouTube UI elements) ──
SAFE_TOP    = 180    # Top 180px (system bar + search)
SAFE_BOTTOM = 300    # Bottom 300px (like/comment/share buttons)
TEXT_ZONE_TOP = 200
TEXT_ZONE_BOT = HEIGHT - 320


def get_font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for f in candidates:
        try:
            return ImageFont.truetype(f, size)
        except Exception:
            continue
    return ImageFont.load_default()


def fetch_image_from_url(url, timeout=60):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            img = Image.open(BytesIO(data)).convert("RGB")
            if img.size[0] > 10 and img.size[1] > 10:
                return img
    except Exception as e:
        log.warning(f"Fetch failed from {url[:60]}: {e}")
    return None


# ══════════════════════════════════════════════════════════════════
#  CINEMATIC AI IMAGE GENERATION
# ══════════════════════════════════════════════════════════════════

def generate_ai_image_cinematic(scene_description: str, style: str = "cinematic") -> Optional[Image.Image]:
    """
    Generate viral-quality AI images with cinematic prompts.
    Styles: cinematic, dark, mysterious, dramatic, glowing
    """
    style_prompts = {
        "cinematic": (
            f"{scene_description}, cinematic lighting, dramatic shadows, "
            f"hyper detailed, professional photography, 8k quality, "
            f"vibrant colors, shallow depth of field, lens flare, "
            f"dark moody atmosphere, no text, no watermark"
        ),
        "dark": (
            f"{scene_description}, dark atmospheric, noir style, "
            f"dramatic rim lighting, mysterious fog, deep shadows, "
            f"high contrast, cinematic color grading, 8k, no text"
        ),
        "mysterious": (
            f"{scene_description}, mysterious ethereal glow, "
            f"neon accents in blue and purple, dark background, "
            f"sci-fi atmosphere, volumetric lighting, 8k, no text"
        ),
        "dramatic": (
            f"{scene_description}, ultra dramatic composition, "
            f"bold colors red and gold, epic scale, "
            f"professional studio lighting, photorealistic, 8k, no text"
        ),
        "glowing": (
            f"{scene_description}, bioluminescent glow effect, "
            f"neon cyan highlights, dark background, "
            f"ethereal atmosphere, particle effects, 8k, no text"
        ),
    }

    prompt = style_prompts.get(style, style_prompts["cinematic"])
    encoded = urllib.parse.quote(prompt)

    # Try multiple image APIs with different styles
    apis = [
        ("Pollinations flux", f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1920&nologo=true&model=flux&seed={random.randint(1,99999)}"),
        ("Pollinations turbo", f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1920&nologo=true&model=turbo&seed={random.randint(1,99999)}"),
    ]

    for name, url in apis:
        log.info(f"Trying {name}...")
        img = fetch_image_from_url(url, timeout=60)
        if img:
            log.info(f"{name} succeeded")
            # Ensure correct aspect ratio
            img = img.resize((WIDTH, HEIGHT), Image.LANCZOS)
            return img

    return None


def create_dramatic_fallback(scene_num: int, narration: str, title: str) -> Image.Image:
    """
    Create a visually striking fallback card when APIs fail.
    Dark background with glowing geometric elements and bold text.
    """
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Dramatic gradient background
    for y in range(HEIGHT):
        r = int(10 + 15 * math.sin(y / 400 + scene_num))
        g = int(10 + 8 * math.sin(y / 300 + scene_num * 2))
        b = int(20 + 20 * math.sin(y / 250 + scene_num * 3))
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    # Glowing circles
    colors = [
        (0, 212, 255),    # Cyan
        (123, 47, 190),   # Purple
        (255, 50, 50),    # Red
        (255, 220, 0),    # Yellow
    ]
    accent = colors[scene_num % len(colors)]

    # Large glowing circle
    cx, cy = WIDTH // 2, HEIGHT // 3
    for radius in range(350, 0, -5):
        alpha = max(0, min(255, int(80 * (1 - radius / 350))))
        color = tuple(int(c * alpha / 255) for c in accent)
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                     outline=color, width=2)

    # Inner bright circle
    draw.ellipse([cx - 120, cy - 120, cx + 120, cy + 120],
                 fill=accent, outline=(255, 255, 255), width=4)

    # Scene number in circle
    font_num = get_font(120, bold=True)
    num_text = str(scene_num)
    bbox = draw.textbbox((0, 0), num_text, font=font_num)
    nx = cx - (bbox[2] - bbox[0]) // 2
    ny = cy - (bbox[3] - bbox[1]) // 2
    draw.text((nx, ny), num_text, font=font_num, fill=TEXT_WHITE)

    # Bold title text at bottom
    font_title = get_font(72, bold=True)
    wrapped = textwrap.wrap(title.upper(), width=18)
    ty = HEIGHT // 2 + 100
    for line in wrapped[:3]:
        bbox = draw.textbbox((0, 0), line, font=font_title)
        tx = (WIDTH - (bbox[2] - bbox[0])) // 2
        # Text shadow
        draw.text((tx + 3, ty + 3), line, font=font_title, fill=TEXT_SHADOW)
        draw.text((tx, ty), line, font=font_title, fill=TEXT_WHITE)
        ty += (bbox[3] - bbox[1]) + 20

    # Bottom channel branding
    font_brand = get_font(40, bold=True)
    brand_text = f"▸ {CHANNEL_NAME}"
    bbox = draw.textbbox((0, 0), brand_text, font=font_brand)
    draw.text(((WIDTH - (bbox[2] - bbox[0])) // 2, HEIGHT - 150),
              brand_text, font=font_brand, fill=ACCENT_CYAN)

    return img


# ══════════════════════════════════════════════════════════════════
#  THUMBNAIL GENERATION (viral clickbait style)
# ══════════════════════════════════════════════════════════════════

def generate_thumbnail(script_data: str, output_path: str) -> str:
    """
    Generate a viral-style thumbnail: high contrast, bold text, dramatic.
    1280x720 landscape format for YouTube.
    """
    thumb_w, thumb_h = 1280, 720
    img = Image.new("RGB", (thumb_w, thumb_h), (10, 10, 15))
    draw = ImageDraw.Draw(img)

    title = script_data.get("title", "SECRET Psychology Trick")
    hook = script_data.get("hook", "")

    # Dramatic gradient background
    for y in range(thumb_h):
        ratio = y / thumb_h
        r = int(15 + 40 * ratio)
        g = int(5 + 10 * ratio)
        b = int(30 + 50 * (1 - ratio))
        draw.line([(0, y), (thumb_w, y)], fill=(r, g, b))

    # Glowing accent shapes
    for _ in range(5):
        cx = random.randint(0, thumb_w)
        cy = random.randint(0, thumb_h)
        radius = random.randint(80, 200)
        color = random.choice([ACCENT_CYAN, (123, 47, 190), ACCENT_RED])
        for r in range(radius, 0, -3):
            alpha = max(0, min(255, int(60 * (1 - r / radius))))
            c = tuple(int(cl * alpha / 255) for cl in color)
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=c, width=1)

    # Bold title text (large, centered, with outline)
    font_title = get_font(80, bold=True)
    lines = textwrap.wrap(title.upper(), width=16)
    total_h = len(lines) * 95
    ty = (thumb_h - total_h) // 2

    for line in lines[:3]:
        bbox = draw.textbbox((0, 0), line, font=font_title)
        tx = (thumb_w - (bbox[2] - bbox[0])) // 2
        # Thick outline
        for dx in range(-4, 5):
            for dy in range(-4, 5):
                draw.text((tx + dx, ty + dy), line, font=font_title, fill=(0, 0, 0))
        draw.text((tx, ty), line, font=font_title, fill=ACCENT_YELLOW)
        ty += 95

    # "SUBSCRIBE" badge
    badge_font = get_font(36, bold=True)
    badge_text = "▶ SUBSCRIBE"
    bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    bx = thumb_w - (bbox[2] - bbox[0]) - 40
    by = thumb_h - (bbox[3] - bbox[1]) - 30
    draw.rounded_rectangle([bx - 16, by - 8, bx + (bbox[2] - bbox[0]) + 16, by + (bbox[3] - bbox[1]) + 8],
                           radius=12, fill=ACCENT_RED)
    draw.text((bx, by), badge_text, font=badge_font, fill=TEXT_WHITE)

    # Channel logo area
    font_logo = get_font(48, bold=True)
    draw.text((30, 30), CHANNEL_NAME, font=font_logo, fill=ACCENT_CYAN)

    img.save(output_path, "JPEG", quality=95)
    log.info(f"Thumbnail saved: {output_path}")
    return output_path


# ══════════════════════════════════════════════════════════════════
#  DYNAMIC FRAME COMPOSITION
# ══════════════════════════════════════════════════════════════════

def compose_frame_viral(
    ai_image: Image.Image,
    title: str,
    narration_line: str,
    scene_num: int,
    total: int,
    hook_text: str = "",
    zoom_factor: float = 1.0,
    pan_x: float = 0.0,
    pan_y: float = 0.0,
) -> Image.Image:
    """
    Compose a single viral frame with:
    - Full-bleed cinematic image (no borders)
    - Ken Burns zoom/pan effect
    - Bold word-by-word text overlay in center
    - Scene counter badge
    - Channel branding
    """
    canvas = Image.new("RGB", (WIDTH, HEIGHT), BG_DARK)

    # ── Full-bleed image with zoom/pan ──
    if ai_image:
        # Apply zoom factor
        zw = int(WIDTH * zoom_factor)
        zh = int(HEIGHT * zoom_factor)
        zoomed = ai_image.resize((zw, zh), Image.LANCZOS)

        # Calculate crop position for pan
        crop_x = int((zw - WIDTH) * (0.5 + pan_x * 0.3))
        crop_y = int((zh - HEIGHT) * (0.5 + pan_y * 0.3))
        crop_x = max(0, min(crop_x, zw - WIDTH))
        crop_y = max(0, min(crop_y, zh - HEIGHT))

        cropped = zoomed.crop((crop_x, crop_y, crop_x + WIDTH, crop_y + HEIGHT))
        canvas.paste(cropped, (0, 0))

    # ── Dark gradient overlay for text readability ──
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    # Top gradient (darker)
    for y in range(0, 400):
        alpha = int(180 * (1 - y / 400))
        ov_draw.line([(0, y), (WIDTH, y)], fill=(0, 0, 0, alpha))
    # Bottom gradient (darker)
    for y in range(HEIGHT - 500, HEIGHT):
        alpha = int(200 * ((y - (HEIGHT - 500)) / 500))
        ov_draw.line([(0, y), (WIDTH, y)], fill=(0, 0, 0, alpha))
    canvas.paste(Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB"))

    draw = ImageDraw.Draw(canvas)

    # ── Hook text at top (if first scene) ──
    if hook_text and scene_num == 1:
        font_hook = get_font(52, bold=True)
        hook_upper = hook_text.upper()
        wrapped = textwrap.wrap(hook_upper, width=22)
        hy = SAFE_TOP + 20
        for line in wrapped[:2]:
            bbox = draw.textbbox((0, 0), line, font=font_hook)
            hx = (WIDTH - (bbox[2] - bbox[0])) // 2
            # Background pill
            pad = 16
            draw.rounded_rectangle(
                [hx - pad, hy - pad // 2, hx + (bbox[2] - bbox[0]) + pad, hy + (bbox[3] - bbox[1]) + pad],
                radius=20, fill=(0, 0, 0, 180) if hasattr(draw, '_image') else (20, 20, 30)
            )
            draw.text((hx, hy), line, font=font_hook, fill=ACCENT_YELLOW)
            hy += (bbox[3] - bbox[1]) + 16

    # ── Bold narration text (center screen, large) ──
    font_narration = get_font(68, bold=True)
    wrapped = textwrap.wrap(narration_line, width=18)
    total_text_h = len(wrapped) * 88
    start_y = (HEIGHT - total_text_h) // 2

    for idx, line in enumerate(wrapped[:4]):
        bbox = draw.textbbox((0, 0), line, font=font_narration)
        lx = (WIDTH - (bbox[2] - bbox[0])) // 2
        ly = start_y + idx * 88

        # Glow effect (multiple shadow layers)
        for spread in range(6, 0, -1):
            glow_alpha = int(40 * (1 - spread / 6))
            for dx in range(-spread, spread + 1, spread):
                for dy in range(-spread, spread + 1, spread):
                    draw.text((lx + dx, ly + dy), line, font=font_narration,
                              fill=(0, 212, 255) if idx % 2 == 0 else TEXT_WHITE)

        # Main text
        draw.text((lx, ly), line, font=font_narration, fill=TEXT_WHITE)

    # ── Scene counter (bottom left) ──
    counter_font = get_font(38, bold=True)
    counter_text = f"{scene_num}/{total}"
    draw.rounded_rectangle([30, HEIGHT - 120, 130, HEIGHT - 70], radius=16, fill=(0, 0, 0))
    draw.text((50, HEIGHT - 115), counter_text, font=counter_font, fill=ACCENT_CYAN)

    # ── Channel branding (bottom center) ──
    brand_font = get_font(32, bold=True)
    brand_text = CHANNEL_NAME
    bbox = draw.textbbox((0, 0), brand_text, font=brand_font)
    bx = (WIDTH - (bbox[2] - bbox[0])) // 2
    draw.text((bx, HEIGHT - 110), brand_text, font=brand_font, fill=ACCENT_CYAN)

    # ── Progress bar ──
    bar_y = HEIGHT - 55
    bar_h = 6
    bar_w = WIDTH - 120
    bar_x = 60
    progress = scene_num / total
    draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h],
                           radius=3, fill=(50, 50, 50))
    draw.rounded_rectangle([bar_x, bar_y, bar_x + int(bar_w * progress), bar_y + bar_h],
                           radius=3, fill=ACCENT_CYAN)

    return canvas


# ══════════════════════════════════════════════════════════════════
#  SCENE BUILDING
# ══════════════════════════════════════════════════════════════════

def build_scenes_viral(script_data: dict) -> list:
    """
    Build scenes optimized for viral pacing:
    - 4-6 scenes for 20-35 second videos
    - Each scene = 1 key sentence
    - Dramatic image prompts per scene
    """
    script = script_data.get("script", "")
    sections = script_data.get("sections", [])

    # Split into individual sentences
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', script) if len(s.strip()) > 10]

    # Target 5 scenes for optimal viral pacing
    target_scenes = min(6, max(4, len(sentences) // 2))

    if len(sentences) <= target_scenes:
        narrations = sentences
    else:
        # Pick the most impactful sentences
        step = len(sentences) / target_scenes
        narrations = [sentences[int(i * step)] for i in range(target_scenes)]

    # Viral image prompt styles
    visual_styles = [
        "dramatic close-up portrait with intense expression, cinematic lighting",
        "mysterious silhouette against glowing neon background, dark atmosphere",
        "abstract neural network visualization, glowing blue connections",
        "dramatic hands reaching toward light, emotional composition",
        "futuristic holographic brain scan, purple and cyan glow",
        "dark corridor with single light source, dramatic shadows",
        "cosmic nebula with human figure silhouette, epic scale",
        "urban night scene with neon reflections, cyberpunk mood",
    ]

    scenes = []
    for i, narr in enumerate(narrations):
        # Get section title if available
        section = sections[i] if i < len(sections) else f"Part {i + 1}"

        # Build cinematic image prompt
        visual = visual_styles[i % len(visual_styles)]
        style = random.choice(["cinematic", "dark", "mysterious", "dramatic", "glowing"])

        scenes.append({
            "section": section,
            "narration": narr,
            "image_prompt": f"{visual}, {narr[:60]}",
            "style": style,
        })

    return scenes


# ══════════════════════════════════════════════════════════════════
#  VIDEO GENERATION (moviepy with motion effects)
# ══════════════════════════════════════════════════════════════════

def generate_video(script_data: dict, audio_path: str, output_path: str) -> bool:
    """
    Generate a viral-quality YouTube Short with:
    - Cinematic AI images
    - Ken Burns zoom/pan motion on every scene
    - Bold animated text overlays
    - Crossfade transitions
    - Dramatic thumbnail
    """
    try:
        try:
            from moviepy.editor import (
                ImageClip, AudioFileClip, concatenate_videoclips,
                CompositeVideoClip
            )
        except (ImportError, ModuleNotFoundError):
            from moviepy import (
                ImageClip, AudioFileClip, concatenate_videoclips,
                CompositeVideoClip
            )
    except ImportError:
        log.error("moviepy not available. Install: pip install moviepy==1.0.3")
        return False

    os.makedirs("output/slides", exist_ok=True)
    os.makedirs("output/thumbnails", exist_ok=True)

    # ── Get audio duration ──
    try:
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        audio.close()
    except Exception as e:
        log.error(f"Cannot read audio: {e}")
        return False

    log.info(f"Audio duration: {duration:.1f}s")

    # ── Build scenes ──
    scenes = build_scenes_viral(script_data)
    total = len(scenes)
    sec_dur = duration / total
    title = script_data.get("title", "Amazing Facts")
    hook = script_data.get("hook", "")

    log.info(f"Building {total} scenes, {sec_dur:.1f}s each")

    clips = []
    for i, scene in enumerate(scenes):
        log.info(f"Scene {i+1}/{total}: {scene['section']}")

        # ── Generate AI image ──
        ai_img = generate_ai_image_cinematic(scene["image_prompt"], scene.get("style", "cinematic"))
        if ai_img is None:
            ai_img = create_dramatic_fallback(i + 1, scene["narration"], title)

        # ── Create multiple frames with Ken Burns effect ──
        # Each scene gets 4-6 frames with different zoom/pan for motion
        num_frames = max(4, int(sec_dur * FPS / 10))  # ~10 frames per second of scene
        frames_dir = f"output/slides/scene_{i+1:03d}"
        os.makedirs(frames_dir, exist_ok=True)

        frame_clips = []
        for f_idx in range(num_frames):
            t = f_idx / max(1, num_frames - 1)  # 0.0 to 1.0

            # Ken Burns parameters
            zoom = 1.0 + 0.15 * math.sin(t * math.pi)  # Zoom in then out
            pan_x = math.sin(t * math.pi * 2) * 0.1      # Pan left-right
            pan_y = math.cos(t * math.pi * 2) * 0.05     # Pan up-down slightly

            frame = compose_frame_viral(
                ai_img, title, scene["narration"],
                i + 1, total, hook,
                zoom_factor=zoom, pan_x=pan_x, pan_y=pan_y,
            )

            frame_path = f"{frames_dir}/frame_{f_idx:03d}.png"
            frame.save(frame_path, "PNG")

            frame_dur = sec_dur / num_frames
            frame_clips.append(ImageClip(frame_path).set_duration(frame_dur))

        # Concatenate frames for this scene
        scene_clip = concatenate_videoclips(frame_clips, method="compose")
        clips.append(scene_clip)
        log.info(f"Scene {i+1} done ({num_frames} frames)")

    # ── Concatenate all scenes ──
    video = concatenate_videoclips(clips, method="compose")

    # ── Add audio ──
    audio = AudioFileClip(audio_path)
    if audio.duration > video.duration:
        audio = audio.subclip(0, video.duration)
    else:
        video = video.set_duration(audio.duration)
    video = video.set_audio(audio)

    # ── Export video ──
    video.write_videofile(
        output_path, fps=FPS, codec="libx264",
        audio_codec="aac", temp_audiofile="output/temp_audio.m4a",
        remove_temp=True, logger=None,
        preset="medium",  # Balance speed vs quality
        bitrate="5000k",  # Good quality for Shorts
    )
    audio.close()
    video.close()

    file_size = os.path.getsize(output_path) / (1024 * 1024)
    log.info(f"Video done: {output_path} ({file_size:.1f} MB)")

    # ── Generate thumbnail ──
    thumb_path = output_path.replace(".mp4", "_thumb.jpg").replace("output/", "output/thumbnails/")
    os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
    generate_thumbnail(script_data, thumb_path)

    return True
