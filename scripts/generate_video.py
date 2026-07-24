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
    Generate professional ASS subtitles — clean, readable, no overlap.
    - Word-by-word karaoke highlighting (\kf) with clean white text
    - Subtle pop-in animation (no bounce that causes overlap)
    - Dark semi-transparent box behind text for readability
    - Big emphasis words in TOP area (not center, no overlap with subs)
    - Channel watermark at bottom
    """
    words = script.split()
    phrases = []
    current = []
    for w in words:
        current.append(w)
        if len(current) >= random.randint(3, 5) or w.endswith(('.', '!', '?')):
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
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,Arial Black,72,&H00FFFFFF,&H0000D4FF,&H00000000,&HB4000000,-1,0,0,0,100,100,2,0,3,4,2,5,80,80,160,1
Style: Glow,Arial Black,72,&H0000D4FF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,2,0,3,0,0,5,80,80,160,1
Style: Emphasis,Arial Black,90,&H0000D4FF,&H00FFFFFF,&H00000000,&HC0000000,-1,0,0,0,100,100,4,0,1,5,3,8,80,80,50,1
Style: Watermark,Arial,28,&H00D4FFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,60,60,25,1

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
            word_dur_cs = max(5, int(word_duration * 100))
            karaoke_parts.append("{\\kf%d}%s" % (word_dur_cs, w))
        karaoke_text = " ".join(karaoke_parts)

        # Subtle pop: scale from 95% to 100% (no huge bounce that overlaps)
        pop = "{\\fscx95\\fscy95}{\\t(0,150,\\fscx100\\fscy100)}"

        start_str = _format_ass_time(start_time)
        end_str = _format_ass_time(end_time)

        # Main karaoke line only (no separate glow layer = no overlap)
        ass_content += f"Dialogue: 0,{start_str},{end_str},Main,,0,0,0,,{pop}{karaoke_text}\n"

        # Subtle glow layer — same size, just color shift, behind via layer -1
        ass_content += f"Dialogue: -1,{start_str},{end_str},Glow,,0,0,0,,{pop}{karaoke_text}\n"

    # Channel watermark — small, bottom center
    ass_content += "Dialogue: 1,0:00:00.00,%s,Watermark,,0,0,0,,{\\fad(600,600)}{\\pos(540,1890)}MindRank\n" % _format_ass_time(audio_duration)

    # Big emphasis words — TOP area (y=350), not center, never overlaps with subs
    emphasis_words = ["NEVER", "ALWAYS", "SECRET", "TRUTH", "DANGER", "POWER", "MIND", "BRAIN", "WHY?"]
    for t_sec in range(4, int(audio_duration), 6):
        word = random.choice(emphasis_words)
        t_start = _format_ass_time(t_sec)
        t_end = _format_ass_time(min(t_sec + 2.0, audio_duration))
        ass_content += f"Dialogue: 2,{t_start},{t_end},Emphasis,,0,0,0,,{{\\fad(250,350)}}{{\\pos(540,350)}}{word}\n"

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    log.info(f"ASS subtitles generated: {output_path}")
    return output_path


# ══════════════════════════════════════════════════════════════════
#  THUMBNAIL GENERATOR (Maximum Clickbait)
# ══════════════════════════════════════════════════════════════════

def generate_thumbnail(script_data: dict, output_path: str) -> str:
    """Generate maximum-impact clickbait thumbnail with face/expression and bold text."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont

    thumb_w, thumb_h = 1280, 720
    img = Image.new("RGB", (thumb_w, thumb_h), (5, 5, 12))
    draw = ImageDraw.Draw(img)

    title = script_data.get("title", "THE SECRET NOBODY TELLS YOU")
    # Remove prefixes like "Why:", "Secret:" etc for cleaner display
    clean_title = title
    for prefix in ["Why:", "Secret:", "Dark Truth:", "Shocking:", "Hidden:", "The Real Truth:"]:
        if clean_title.startswith(prefix):
            clean_title = clean_title[len(prefix):].strip()
            break

    # Dramatic dark gradient with subtle color shift
    for y in range(thumb_h):
        ratio = y / thumb_h
        r = int(8 + 25 * math.sin(ratio * 3.5))
        g = int(2 + 6 * ratio)
        b = int(18 + 50 * (1 - ratio) + 15 * math.sin(ratio * 2))
        draw.line([(0, y), (thumb_w, y)], fill=(r, g, b))

    # Big glowing orbs in background
    for _ in range(8):
        cx = random.randint(-50, thumb_w + 50)
        cy = random.randint(-50, thumb_h + 50)
        radius = random.randint(60, 200)
        color = random.choice([ACCENT_CYAN, (123, 47, 187), (255, 50, 50)])
        r, g, b = color
        for i in range(radius, 0, -4):
            alpha_factor = (1 - i / radius) ** 2
            a = int(35 * alpha_factor)
            if a < 1:
                continue
            draw.ellipse([cx - i, cy - i, cx + i, cy + i], fill=(r, g, b))

    # Draw a simple face on the left (draws attention)
    face_cx, face_cy = 200, 360
    face_r = 90
    # Face circle
    draw.ellipse([face_cx - face_r, face_cy - face_r, face_cx + face_r, face_cy + face_r],
                 fill=(220, 180, 150))
    # Eyes (wide open = shock)
    eye_y = face_cy - 20
    for ex in [face_cx - 30, face_cx + 30]:
        # White
        draw.ellipse([ex - 16, eye_y - 14, ex + 16, eye_y + 14], fill=(255, 255, 255))
        # Pupil
        draw.ellipse([ex - 8, eye_y - 8, ex + 8, eye_y + 8], fill=(20, 20, 30))
        # Glint
        draw.ellipse([ex + 4, eye_y - 6, ex + 8, eye_y - 2], fill=(255, 255, 255))
    # Mouth (open = shock)
    mouth_y = face_cy + 35
    draw.ellipse([face_cx - 18, mouth_y - 12, face_cx + 18, mouth_y + 18],
                 fill=(150, 50, 50))
    # Eyebrows (raised)
    draw.line([face_cx - 40, eye_y - 28, face_cx - 12, eye_y - 22],
              fill=(80, 50, 30), width=5)
    draw.line([face_cx + 12, eye_y - 22, face_cx + 40, eye_y - 28],
              fill=(80, 50, 30), width=5)

    # Arrow pointing from face to text
    draw.polygon([(340, 360), (380, 340), (380, 380)], fill=ACCENT_YELLOW)

    # BIG title text with glow — right side
    font = get_font(88, bold=True)
    lines = textwrap.wrap(clean_title.upper(), width=14)
    total_h = len(lines) * 100
    ty = (thumb_h - total_h) // 2

    for line in lines[:3]:
        bbox = draw.textbbox((0, 0), line, font=font)
        tx = max(400, (thumb_w - (bbox[2] - bbox[0])) // 2)

        # Glow behind text
        glow_img = Image.new("RGB", (thumb_w, thumb_h), (0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_img)
        glow_draw.text((tx, ty), line, font=font, fill=ACCENT_YELLOW)
        glow_img = glow_img.filter(ImageFilter.GaussianBlur(14))
        img = Image.blend(img, glow_img, 0.45)
        draw = ImageDraw.Draw(img)

        # Thick black outline
        for dx in range(-5, 6):
            for dy in range(-5, 6):
                draw.text((tx + dx, ty + dy), line, font=font, fill=(0, 0, 0))

        # Main text — yellow with slight gradient feel
        draw.text((tx, ty), line, font=font, fill=ACCENT_YELLOW)
        ty += 100

    # Red "SUBSCRIBE" badge — bottom right
    badge_font = get_font(40, bold=True)
    badge_text = "SUBSCRIBE"
    bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    bw = bbox[2] - bbox[0]
    bh = bbox[3] - bbox[1]
    bx = thumb_w - bw - 45
    by = thumb_h - bh - 35
    # Red rounded rect with shadow
    draw.rounded_rectangle([bx - 25, by - 16, bx + bw + 25, by + bh + 16],
                           radius=18, fill=(200, 0, 0))
    draw.rounded_rectangle([bx - 22, by - 14, bx + bw + 22, by + bh + 14],
                           radius=16, fill=ACCENT_RED)
    draw.text((bx, by), badge_text, font=badge_font, fill=(255, 255, 255))

    # Channel name — top left with glow
    logo_font = get_font(52, bold=True)
    logo_glow = Image.new("RGB", (thumb_w, thumb_h), (0, 0, 0))
    logo_glow_draw = ImageDraw.Draw(logo_glow)
    logo_glow_draw.text((30, 22), "MindRank", font=logo_font, fill=ACCENT_CYAN)
    logo_glow = logo_glow.filter(ImageFilter.GaussianBlur(10))
    img = Image.blend(img, logo_glow, 0.35)
    draw = ImageDraw.Draw(img)
    draw.text((30, 22), "MindRank", font=logo_font, fill=ACCENT_CYAN)

    img.save(output_path, "JPEG", quality=95)
    log.info(f"Thumbnail saved: {output_path}")
    return output_path


# ══════════════════════════════════════════════════════════════════
#  MAIN VIDEO COMPOSITION
# ══════════════════════════════════════════════════════════════════

def generate_video(script_data: dict, audio_path: str, output_dir: str) -> str:
    """
    Generate viral short video — randomly alternates between:
    - Stock footage mode (Pexels real video + karaoke subs)
    - Character animation mode (Pillow flat-design characters + karaoke subs)
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

    # Randomly choose mode: 55% stock footage, 45% character animation
    mode = random.choices(
        ["stock", "characters"],
        weights=[55, 45],
        k=1
    )[0]
    log.info(f"Video mode: {mode}")

    # Step 1: Create background
    script_text = script_data.get("script", "")
    bg_path = os.path.join(work_dir, f"{base}_bg.mp4")

    if mode == "stock":
        stock_clips = get_stock_for_script(script_text, work_dir, audio_duration)
        if stock_clips and len(stock_clips) >= 2:
            log.info(f"Compositing {len(stock_clips)} stock clips...")
            success = concatenate_clips(stock_clips, bg_path, audio_duration + 1)
            if not success:
                stock_clips = []
        else:
            stock_clips = []

        if not stock_clips:
            log.info("No stock footage, falling back to characters")
            mode = "characters"

    if mode == "characters":
        stock_clips = []
        log.info("Generating character animation frames...")
        _generate_character_bg(script_text, audio_duration, bg_path)

    # Step 2: Generate ASS subtitles
    ass_path = os.path.join(work_dir, f"{base}.ass")
    generate_ass_subtitles(script_text, audio_duration, ass_path)

    # Step 3: Composite everything with FFmpeg
    log.info("Compositing final video...")

    if mode == "stock":
        # Darken + vignette + subtitles for stock footage
        filter_complex = (
            f"[0:v]eq=brightness=-0.08:contrast=1.1,"
            f"vignette=PI/4.5,"
            f"ass={ass_path}"
            f"[final]"
        )
    else:
        # Just subtitles for character animation (already dark background)
        filter_complex = (
            f"[0:v]ass={ass_path}[final]"
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

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

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
            f"[0:v]ass={ass_path}[final]",
            "-map", "[final]", "-map", "1:a",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            "-movflags", "+faststart",
            video_path
        ]
        result2 = subprocess.run(cmd_simple, capture_output=True, text=True, timeout=300)
        if result2.returncode != 0:
            log.error(f"Fallback failed: {result2.stderr[:300]}")
            return ""
        size_mb = os.path.getsize(video_path) / (1024 * 1024)
        log.info(f"Video done (fallback): {video_path} ({size_mb:.1f} MB)")

    # Step 4: Generate thumbnail
    generate_thumbnail(script_data, thumb_path)
    script_data["thumbnail_path"] = thumb_path

    # Cleanup
    cleanup_files = stock_clips + [bg_path]
    for f in cleanup_files:
        try:
            if f and os.path.exists(f) and f != video_path:
                os.remove(f)
        except OSError:
            pass

    return video_path


def _generate_character_bg(script: str, audio_duration: float, output_path: str):
    """
    Render character animation frames using Pillow and pipe to FFmpeg.
    Shows flat-design characters matching the script content.
    """
    from scripts.characters import render_character_animation, W as CHAR_W, H as CHAR_H

    fps = 15  # Lower fps for character frames (faster to render)
    total_frames = int(audio_duration * fps)

    log.info(f"Rendering {total_frames} character frames at {fps}fps...")

    # Start FFmpeg process to receive frames via pipe
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-pix_fmt", "rgba",
        "-s", f"{CHAR_W}x{CHAR_H}",
        "-r", str(fps),
        "-i", "pipe:0",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "26",
        "-pix_fmt", "yuv420p",
        "-t", str(audio_duration + 0.5),
        output_path
    ]

    try:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

        # Render frames and pipe directly to FFmpeg
        from scripts.characters import split_into_scenes, render_scene_frame

        scenes = split_into_scenes(script)
        n_scenes = len(scenes)
        scene_duration = audio_duration / n_scenes if n_scenes > 0 else audio_duration

        for frame_idx in range(total_frames):
            t = frame_idx / fps
            scene_idx = min(int(t / scene_duration), n_scenes - 1)
            scene = scenes[scene_idx]
            local_t = t - scene_idx * scene_duration

            frame = render_scene_frame(scene, local_t, scene_duration)

            # Convert RGBA to raw bytes and write to pipe
            proc.stdin.write(frame.tobytes())

            if frame_idx % (fps * 5) == 0:
                log.info(f"  Characters: frame {frame_idx}/{total_frames}")

        proc.stdin.close()
        stdout, stderr = proc.communicate(timeout=60)

        if proc.returncode != 0:
            log.error(f"Character FFmpeg error: {stderr.decode()[:300]}")
            _generate_fallback_bg(output_path, audio_duration + 1)
        else:
            log.info(f"Character animation saved: {output_path}")

    except Exception as e:
        log.error(f"Character render failed: {e}")
        _generate_fallback_bg(output_path, audio_duration + 1)


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
