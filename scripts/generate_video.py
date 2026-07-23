"""
Step 3: Generate YouTube Shorts video
- Multiple free AI image sources with automatic fallback
- Vertical 1080x1920 Shorts format
- Cartoon illustrations + voiceover, Storywise style
"""

import os
import re
import time
import textwrap
import logging
import urllib.request
import urllib.parse
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

log = logging.getLogger(__name__)

WIDTH        = 1080
HEIGHT       = 1920
FPS          = 30
CHANNEL_NAME = "MindRank"
ACCENT_COLOR = (0, 212, 255)
TEXT_COLOR   = (30, 30, 30)
BG_COLOR     = (13, 17, 23)


def get_font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/ariblk.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for f in candidates:
        try:
            return ImageFont.truetype(f, size)
        except Exception:
            continue
    return ImageFont.load_default()


def fetch_image_from_url(url, timeout=60):
    """Fetch image from any URL, return PIL Image or None."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            img  = Image.open(BytesIO(data)).convert("RGB")
            if img.size[0] > 10 and img.size[1] > 10:
                return img
    except Exception as e:
        log.warning(f"Fetch failed from {url[:60]}: {e}")
    return None


def generate_ai_image(scene_description: str) -> Optional[Image.Image]:
    """
    Try multiple free image APIs in order until one works.
    All completely free, no API key needed.
    """
    prompt = (
        f"{scene_description}, hand drawn cartoon illustration, "
        f"simple clean lines, warm colors, storybook art, "
        f"educational, white background, no text"
    )
    encoded = urllib.parse.quote(prompt)

    # ── API 1: Pollinations (flux model) ──
    log.info(f"Trying Pollinations flux...")
    url1 = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1440&nologo=true&model=flux&seed={int(time.time())}"
    img  = fetch_image_from_url(url1, timeout=45)
    if img:
        log.info("Pollinations flux succeeded")
        return img

    # ── API 2: Pollinations (turbo model) ──
    log.info("Trying Pollinations turbo...")
    url2 = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1440&nologo=true&model=turbo"
    img  = fetch_image_from_url(url2, timeout=45)
    if img:
        log.info("Pollinations turbo succeeded")
        return img

    # ── API 3: Picsum (random beautiful photo as background) ──
    log.info("Trying Picsum photo...")
    seed = abs(hash(scene_description)) % 1000
    url3 = f"https://picsum.photos/seed/{seed}/1080/1440"
    img  = fetch_image_from_url(url3, timeout=20)
    if img:
        log.info("Picsum succeeded — using photo background")
        return apply_cartoon_filter(img)

    log.warning("All image APIs failed — using illustrated fallback")
    return None


def apply_cartoon_filter(img: Image.Image) -> Image.Image:
    """Make a photo look more like an illustration."""
    from PIL import ImageFilter, ImageEnhance
    img = img.filter(ImageFilter.SMOOTH_MORE)
    img = ImageEnhance.Color(img).enhance(0.7)
    img = ImageEnhance.Contrast(img).enhance(1.2)
    return img


def create_illustrated_fallback(scene_num: int, narration: str) -> Image.Image:
    """
    Create a beautiful illustrated card when all APIs fail.
    Uses geometric shapes and colors to look clean and modern.
    """
    img  = Image.new("RGB", (WIDTH, 1440), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Background pattern
    colors = [
        [(255,220,160),(255,200,100)],
        [(160,200,255),(100,160,255)],
        [(160,255,200),(100,220,160)],
        [(255,160,200),(220,100,160)],
    ]
    c = colors[scene_num % len(colors)]

    # Diagonal gradient bands
    for i in range(0, WIDTH + 1440, 120):
        draw.polygon([(i,0),(i+100,0),(i+100-1440,1440),(i-1440,1440)],
                     fill=(*c[0], 40))

    # Large decorative circle
    draw.ellipse([140, 200, 940, 1000], fill=c[0], outline=c[1], width=8)
    draw.ellipse([240, 300, 840, 900],  fill=(255,255,255))

    # Icon based on scene number
    icons = ["?", "!", "★", "♦", "▲"]
    icon  = icons[scene_num % len(icons)]
    font_icon = get_font(300, bold=True)
    bbox = draw.textbbox((0,0), icon, font=font_icon)
    ix   = (WIDTH - (bbox[2]-bbox[0])) // 2
    draw.text((ix, 340), icon, font=font_icon, fill=ACCENT_COLOR)

    # Narration preview text
    font_text = get_font(58)
    wrapped   = textwrap.wrap(narration[:120], width=20)
    y = 1060
    for line in wrapped[:3]:
        bbox = draw.textbbox((0,0), line, font=font_text)
        draw.text(((WIDTH-(bbox[2]-bbox[0]))//2, y), line,
                  font=font_text, fill=(60,60,60))
        y += 74

    return img


def compose_frame(ai_image, title, narration, scene_num, total, out_path):
    """Compose full 1080x1920 Shorts frame."""
    canvas = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw   = ImageDraw.Draw(canvas)

    # ── Orange title bar ──
    draw.rectangle([0, 0, WIDTH, 120], fill=ACCENT_COLOR)
    font_t = get_font(58, bold=True)
    bbox   = draw.textbbox((0,0), CHANNEL_NAME, font=font_t)
    draw.text(((WIDTH-(bbox[2]-bbox[0]))//2, (120-(bbox[3]-bbox[1]))//2),
              CHANNEL_NAME, font=font_t, fill=(255,255,255))

    # Scene badge
    badge  = f"{scene_num}/{total}"
    font_b = get_font(44)
    draw.rounded_rectangle([WIDTH-140, 18, WIDTH-18, 102], radius=18, fill=(255,255,255))
    bbox   = draw.textbbox((0,0), badge, font=font_b)
    draw.text((WIDTH-140+(122-(bbox[2]-bbox[0]))//2, 18+(84-(bbox[3]-bbox[1]))//2),
              badge, font=font_b, fill=ACCENT_COLOR)

    # ── AI image ──
    img_top = 130
    img_h   = 1280
    if ai_image:
        pasted = ai_image.resize((WIDTH, img_h), Image.LANCZOS)
        canvas.paste(pasted, (0, img_top))
    else:
        draw.rectangle([0, img_top, WIDTH, img_top+img_h], fill=(220,215,205))

    # ── Text card ──
    card_top = img_top + img_h + 16
    draw.rounded_rectangle([24, card_top, WIDTH-24, HEIGHT-24],
                            radius=28, fill=(255,255,255),
                            outline=ACCENT_COLOR, width=4)

    font_body = get_font(50, bold=True)
    wrapped   = textwrap.wrap(narration, width=24)
    ty = card_top + 26
    for line in wrapped[:4]:
        bbox = draw.textbbox((0,0), line, font=font_body)
        draw.text(((WIDTH-(bbox[2]-bbox[0]))//2, ty),
                  line, font=font_body, fill=TEXT_COLOR)
        ty += (bbox[3]-bbox[1]) + 12

    # ── Progress dots ──
    dot_y = HEIGHT - 52
    gap   = 38
    x0    = (WIDTH - total*gap) // 2
    for i in range(total):
        cx = x0 + i*gap + gap//2
        if i+1 == scene_num:
            draw.ellipse([cx-15, dot_y-15, cx+15, dot_y+15], fill=ACCENT_COLOR)
        else:
            draw.ellipse([cx-8,  dot_y-8,  cx+8,  dot_y+8],  fill=(180,180,180))

    canvas.save(out_path, "PNG")
    return out_path


def build_scenes(script_data):
    script   = script_data.get("script", "")
    sections = script_data.get("sections", ["Introduction", "Main Content", "Conclusion"])
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', script) if len(s.strip()) > 8]
    per    = max(1, len(sentences) // len(sections))
    scenes = []
    for i, sec in enumerate(sections):
        start = i * per
        end   = start + per if i < len(sections)-1 else len(sentences)
        narr  = " ".join(sentences[start:end]) or f"Discover {sec}"
        scenes.append({
            "section":      sec,
            "narration":    narr,
            "image_prompt": f"{sec}: {narr[:80]}, cartoon character explaining concept"
        })
    return scenes


def generate_video(script_data, audio_path, output_path):
    try:
        from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    except ImportError:
        log.error("Run: pip install moviepy==1.0.3")
        return False

    os.makedirs("output/slides", exist_ok=True)

    try:
        audio    = AudioFileClip(audio_path)
        duration = audio.duration
        audio.close()
    except Exception as e:
        log.error(f"Cannot read audio: {e}")
        return False

    scenes  = build_scenes(script_data)
    total   = len(scenes)
    sec_dur = duration / total
    title   = script_data.get("title", "Amazing Facts")
    clips   = []

    for i, scene in enumerate(scenes):
        log.info(f"Scene {i+1}/{total}: {scene['section']}")
        ai_img = generate_ai_image(scene["image_prompt"])
        if ai_img is None:
            ai_img = create_illustrated_fallback(i, scene["narration"])

        path = f"output/slides/scene_{i+1:03d}.png"
        compose_frame(ai_img, title, scene["narration"], i+1, total, path)
        clips.append(ImageClip(path).set_duration(sec_dur))
        log.info(f"Scene {i+1} done")
        if i < total-1:
            time.sleep(1)

    video = concatenate_videoclips(clips, method="compose")
    audio = AudioFileClip(audio_path)
    if audio.duration > video.duration:
        audio = audio.subclip(0, video.duration)
    else:
        video = video.set_duration(audio.duration)
    video = video.set_audio(audio)
    video.write_videofile(output_path, fps=FPS, codec="libx264",
                          audio_codec="aac", temp_audiofile="output/temp_audio.m4a",
                          remove_temp=True, logger=None)
    audio.close()
    video.close()
    log.info(f"Done: {output_path} ({os.path.getsize(output_path)/1024/1024:.1f} MB)")
    return True