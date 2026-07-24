"""
Viral YouTube Shorts Generator — 3 modes: Stock footage, Gameplay loop, Characters
All with ASS karaoke captions + always-visible background.
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
#  ASS KARAOKE SUBTITLES
# ══════════════════════════════════════════════════════════════════

def _format_ass_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def generate_ass_subtitles(script: str, audio_duration: float, output_path: str):
    """Generate ASS subtitles with word-level karaoke timing and BigWord emphasis."""
    words = script.split()
    if not words:
        return

    words_per_sec = len(words) / audio_duration if audio_duration > 0 else 3.0
    chunk_size = max(2, min(5, int(words_per_sec * 1.2)))
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunk_words = words[i:i + chunk_size]
        chunks.append(" ".join(chunk_words))

    n_chunks = len(chunks)
    chunk_dur = audio_duration / n_chunks if n_chunks > 0 else audio_duration

    header = """[Script Info]
Title: MindRank Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,68,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3.5,1.5,2,40,40,600,1
Style: BigWord,Arial Black,82,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,8,40,40,150,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events = []
    for i, chunk in enumerate(chunks):
        start = i * chunk_dur
        end = start + chunk_dur
        start_t = _format_ass_time(start)
        end_t = _format_ass_time(end)

        words_in_chunk = chunk.split()
        if not words_in_chunk:
            continue

        big_word = max(words_in_chunk, key=len)
        karaoke_parts = []
        for w in words_in_chunk:
            w_dur = int(chunk_dur * 100 / len(words_in_chunk))
            if w == big_word:
                karaoke_parts.append(f"{{\\kf{w_dur}}}{w}")
            else:
                karaoke_parts.append(f"{{\\kf{w_dur}}}{w}")
        karaoke_text = " ".join(karaoke_parts)

        events.append(
            f"Dialogue: 0,{start_t},{end_t},Default,,0,0,0,,{karaoke_text}"
        )

        big_dur = int(chunk_dur * 40)
        events.append(
            f"Dialogue: 1,{start_t},{end_t},BigWord,,0,0,0,,{{\\fad(200,200)\\pos(540,180)\\kf{big_dur}}}{big_word}"
        )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")

    log.info(f"ASS subtitles generated: {output_path}")


# ══════════════════════════════════════════════════════════════════
#  THUMBNAIL GENERATOR (YouTube cover — what people see before clicking)
# ══════════════════════════════════════════════════════════════════

def generate_thumbnail(script_data: dict, output_path: str) -> str:
    """Generate super-clickbait thumbnail for YouTube Shorts cover.

    This is the static image shown on the channel page and in search results.
    NOT shown inside the video itself.
    """
    from PIL import Image, ImageDraw, ImageFilter

    thumb_w, thumb_h = 1280, 720
    img = Image.new("RGB", (thumb_w, thumb_h), (5, 5, 12))
    draw = ImageDraw.Draw(img)

    title = script_data.get("title", "THE SECRET NOBODY TELLS YOU")
    clean_title = title
    for prefix in ["Why:", "Secret:", "Dark Truth:", "Shocking:", "Hidden:", "The Real Truth:"]:
        if clean_title.startswith(prefix):
            clean_title = clean_title[len(prefix):].strip()
            break

    # Dramatic gradient background
    for y in range(thumb_h):
        ratio = y / thumb_h
        r = int(8 + 40 * math.sin(ratio * 3.5))
        g = int(2 + 8 * ratio)
        b = int(18 + 60 * (1 - ratio) + 20 * math.sin(ratio * 2))
        draw.line([(0, y), (thumb_w, y)], fill=(r, g, b))

    # Glowing orbs for drama
    for _ in range(12):
        cx = random.randint(-50, thumb_w + 50)
        cy = random.randint(-50, thumb_h + 50)
        radius = random.randint(80, 250)
        color = random.choice([ACCENT_CYAN, (123, 47, 187), (255, 50, 50), ACCENT_YELLOW])
        r, g, b = color
        for i in range(radius, 0, -4):
            alpha_factor = (1 - i / radius) ** 2
            a = int(50 * alpha_factor)
            if a < 1:
                continue
            draw.ellipse([cx - i, cy - i, cx + i, cy + i], fill=(r, g, b))

    # Shocked face on the left
    face_cx, face_cy = 200, 360
    face_r = 100
    draw.ellipse([face_cx - face_r, face_cy - face_r, face_cx + face_r, face_cy + face_r],
                 fill=(220, 180, 150))
    # Wide shocked eyes
    eye_y = face_cy - 25
    for ex in [face_cx - 32, face_cx + 32]:
        draw.ellipse([ex - 20, eye_y - 18, ex + 20, eye_y + 18], fill=(255, 255, 255))
        draw.ellipse([ex - 10, eye_y - 10, ex + 10, eye_y + 10], fill=(20, 20, 30))
        draw.ellipse([ex + 3, eye_y - 7, ex + 9, eye_y - 1], fill=(255, 255, 255))
    # Open mouth (shocked)
    mouth_y = face_cy + 40
    draw.ellipse([face_cx - 22, mouth_y - 16, face_cx + 22, mouth_y + 22], fill=(150, 50, 50))
    # Raised eyebrows
    draw.line([face_cx - 45, eye_y - 35, face_cx - 10, eye_y - 28], fill=(80, 50, 30), width=6)
    draw.line([face_cx + 10, eye_y - 28, face_cx + 45, eye_y - 35], fill=(80, 50, 30), width=6)

    # Yellow arrow pointing to text
    draw.polygon([(340, 360), (400, 330), (400, 390)], fill=ACCENT_YELLOW)

    # BIG bold text — as large as possible, right side
    font = get_font(96, bold=True)
    lines = textwrap.wrap(clean_title.upper(), width=16)
    total_h = len(lines) * 108
    ty = (thumb_h - total_h) // 2

    for line in lines[:3]:
        bbox = draw.textbbox((0, 0), line, font=font)
        tx = max(420, (thumb_w - (bbox[2] - bbox[0])) // 2)

        # Glow
        glow_img = Image.new("RGB", (thumb_w, thumb_h), (0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_img)
        glow_draw.text((tx, ty), line, font=font, fill=ACCENT_YELLOW)
        glow_img = glow_img.filter(ImageFilter.GaussianBlur(16))
        img = Image.blend(img, glow_img, 0.5)
        draw = ImageDraw.Draw(img)

        # Shadow
        for dx in range(-6, 7):
            for dy in range(-6, 7):
                draw.text((tx + dx, ty + dy), line, font=font, fill=(0, 0, 0))
        # Main text
        draw.text((tx, ty), line, font=font, fill=ACCENT_YELLOW)

        ty += 108

    # MindRank logo
    logo_font = get_font(32, bold=True)
    draw.text((30, 22), "MindRank", font=logo_font, fill=ACCENT_CYAN)

    img.save(output_path, "JPEG", quality=95)
    log.info(f"Thumbnail saved: {output_path}")
    return output_path


# ══════════════════════════════════════════════════════════════════
#  ANIMATED BACKGROUND (always works, no dependencies)
# ══════════════════════════════════════════════════════════════════

def _generate_animated_bg(output_path: str, duration: float):
    """Professional animated dark background with moving particles and glow."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i",
        f"color=c=0x0A0A15:s={WIDTH}x{HEIGHT}:d={duration}:r={FPS}",
        "-vf", ",".join([
            f"drawtext=text='●':fontsize=200:fontcolor=0x00D4FF@0.06:"
            f"x='mod(t*30,{WIDTH})':y='h/3+100*sin(t*0.5)'",
            f"drawtext=text='●':fontsize=160:fontcolor=0x7B2FBE@0.06:"
            f"x='mod(t*22+400,{WIDTH})':y='2*h/3+80*cos(t*0.7)'",
            f"drawtext=text='●':fontsize=120:fontcolor=0x00D4FF@0.04:"
            f"x='mod(t*15+200,{WIDTH})':y='h/2+60*sin(t*1.2)'",
            f"drawtext=text='●':fontsize=180:fontcolor=0x7B2FBE@0.05:"
            f"x='mod(t*28+600,{WIDTH})':y='h/4+90*cos(t*0.3)'",
            f"drawtext=text='—':fontsize=80:fontcolor=0x00D4FF@0.03:"
            f"x='mod(t*40+100,{WIDTH})':y='h*0.7+40*sin(t*0.8)'",
            f"drawtext=text='—':fontsize=60:fontcolor=0x7B2FBE@0.03:"
            f"x='mod(t*35+500,{WIDTH})':y='h*0.3+30*cos(t*1.0)'",
            "vignette=PI/4",
        ]),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        output_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=True)
        log.info(f"Animated background: {output_path}")
    except Exception as e:
        log.warning(f"Animated bg failed: {e}")
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i",
            f"color=c=0x0A0A15:s={WIDTH}x{HEIGHT}:d={duration}:r={FPS}",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            output_path
        ], capture_output=True, timeout=60)


# ══════════════════════════════════════════════════════════════════
#  GAMEPLAY BACKGROUND — Endless Runner (Subway Surfers style)
# ══════════════════════════════════════════════════════════════════

def _generate_gameplay_bg(output_path: str, duration: float):
    """Generate a simple endless-runner style animation loop using Pillow.

    Creates a side-scrolling character dodging obstacles on colorful tracks —
    the visual stimulation that keeps viewers watching (Subway Surfers style).
    """
    import tempfile
    import shutil
    from PIL import Image as PILImage, ImageDraw

    fps = 30
    total_frames = int(duration * fps)
    tmp_dir = tempfile.mkdtemp(prefix="gameplay_")

    log.info(f"Generating {total_frames} gameplay frames ({duration:.0f}s)...")

    track_colors = [(0, 150, 255), (255, 80, 80), (80, 220, 120)]
    runner_color = (255, 220, 0)

    lane_y_positions = [HEIGHT * 0.62, HEIGHT * 0.72, HEIGHT * 0.82]

    random.seed(42)
    obstacles = []
    for i in range(int(duration * 3)):
        t_start = random.uniform(0, duration)
        lane = random.randint(0, 2)
        obs_type = random.choice(["box", "barrier", "gap"])
        obs_color = random.choice(track_colors)
        obstacles.append((t_start, lane, obs_type, obs_color))
    obstacles.sort(key=lambda x: x[0])

    coin_positions = []
    for i in range(int(duration * 5)):
        t = random.uniform(0, duration)
        lane = random.randint(0, 2)
        y_offset = random.uniform(-80, 80)
        coin_positions.append((t, lane, y_offset))

    runner_lane = 1
    runner_bob = 0

    for frame_idx in range(total_frames):
        t = frame_idx / fps

        img = PILImage.new("RGB", (WIDTH, HEIGHT), (15, 12, 30))
        draw = ImageDraw.Draw(img)

        # Moving track lines (parallax effect)
        speed = 400
        for lane_i in range(3):
            ly = int(lane_y_positions[lane_i])
            track_color = track_colors[lane_i]
            tr, tg, tb = track_color

            draw.rectangle([0, ly - 3, WIDTH, ly + 3], fill=(tr // 3, tg // 3, tb // 3))

            for stripe_i in range(20):
                stripe_x = int((stripe_i * 120 - (t * speed * (1 + lane_i * 0.3)) % (20 * 120)) % (WIDTH + 120) - 60)
                stripe_w = 60
                alpha = 0.3
                draw.rectangle([stripe_x, ly - 1, stripe_x + stripe_w, ly + 1],
                             fill=(int(tr * alpha), int(tg * alpha), int(tb * alpha)))

        # Coins (spinning effect)
        for ct, clane, cy_off in coin_positions:
            ct_norm = ct % duration
            if abs(t - ct_norm) < 0.15:
                coin_x = int(WIDTH * 0.7 + 40 * math.sin(t * 8))
                coin_y = int(lane_y_positions[clane] - 40 + cy_off)
                coin_r = int(12 + 4 * math.sin(t * 12))
                draw.ellipse([coin_x - coin_r, coin_y - coin_r, coin_x + coin_r, coin_y + coin_r],
                           fill=ACCENT_YELLOW, outline=(200, 180, 0))

        # Obstacles
        for ot, olane, otype, ocolor in obstacles:
            if abs(t - ot) < 0.8:
                ox = int(WIDTH * 0.65 + (t - ot) * 200)
                oy = int(lane_y_positions[olane])
                ocr, ocg, ocb = ocolor

                if otype == "box":
                    draw.rectangle([ox - 25, oy - 45, ox + 25, oy + 5],
                                 fill=ocolor, outline=(255, 255, 255))
                elif otype == "barrier":
                    draw.rectangle([ox - 35, oy - 55, ox + 35, oy + 5],
                                 fill=ocolor, outline=(255, 255, 255))
                    draw.rectangle([ox - 5, oy - 55, ox + 5, oy - 75],
                                 fill=(200, 200, 200))
                else:
                    draw.rectangle([ox - 40, oy + 5, ox + 40, oy + 15],
                                 fill=(200, 50, 50))

        # Runner character (simple stick figure with glow)
        runner_x = int(WIDTH * 0.3)
        runner_y = int(lane_y_positions[runner_lane])
        runner_bob = int(8 * math.sin(t * 10))

        glow_r = 45
        for i in range(glow_r, 0, -3):
            alpha = int(15 * (1 - i / glow_r))
            draw.ellipse([runner_x - i, runner_y - 50 + runner_bob - i,
                        runner_x + i, runner_y - 50 + runner_bob + i],
                       fill=(255, 220, 0, alpha))

        draw.ellipse([runner_x - 14, runner_y - 62 + runner_bob,
                     runner_x + 14, runner_y - 34 + runner_bob], fill=(220, 180, 150))
        draw.rectangle([runner_x - 10, runner_y - 35 + runner_bob,
                       runner_x + 10, runner_y + 5 + runner_bob], fill=runner_color)
        leg_offset = int(12 * math.sin(t * 14))
        draw.line([runner_x - 5, runner_y + 5 + runner_bob,
                  runner_x - 8 + leg_offset, runner_y + 40 + runner_bob], fill=(60, 50, 80), width=5)
        draw.line([runner_x + 5, runner_y + 5 + runner_bob,
                  runner_x + 8 - leg_offset, runner_y + 40 + runner_bob], fill=(60, 50, 80), width=5)
        arm_offset = int(10 * math.sin(t * 14 + 1.5))
        draw.line([runner_x - 8, runner_y - 25 + runner_bob,
                  runner_x - 22 + arm_offset, runner_y - 8 + runner_bob], fill=(60, 50, 80), width=4)
        draw.line([runner_x + 8, runner_y - 25 + runner_bob,
                  runner_x + 22 - arm_offset, runner_y - 8 + runner_bob], fill=(60, 50, 80), width=4)

        # Score display (top right)
        score = int(t * 100)
        score_font = get_font(48, bold=True)
        draw.text((WIDTH - 280, 40), f"SCORE: {score}", font=score_font, fill=ACCENT_YELLOW)

        # Speed lines (motion blur effect)
        for _ in range(8):
            sy = random.randint(100, HEIGHT - 100)
            sx = random.randint(0, WIDTH)
            sl = random.randint(30, 100)
            draw.line([sx, sy, sx - sl, sy], fill=(255, 255, 255), width=1)

        img.save(os.path.join(tmp_dir, f"frame_{frame_idx:05d}.jpg"), "JPEG", quality=85)

        if frame_idx % (fps * 10) == 0 and frame_idx > 0:
            log.info(f"  Gameplay: frame {frame_idx}/{total_frames}")

    log.info("All gameplay frames saved. Encoding with FFmpeg...")
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", os.path.join(tmp_dir, "frame_%05d.jpg"),
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
        "-pix_fmt", "yuv420p",
        "-t", str(duration + 0.5),
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    shutil.rmtree(tmp_dir, ignore_errors=True)

    if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        size_kb = os.path.getsize(output_path) / 1024
        log.info(f"Gameplay background saved: {output_path} ({size_kb:.0f} KB)")
    else:
        log.warning(f"Gameplay FFmpeg failed: {result.stderr[:200]}")
        _generate_animated_bg(output_path, duration + 1)


# ══════════════════════════════════════════════════════════════════
#  CHARACTER ANIMATION (temp files, robust)
# ══════════════════════════════════════════════════════════════════

def _generate_character_bg(script: str, audio_duration: float, output_path: str):
    """Render character frames to temp JPEGs then encode with FFmpeg image2."""
    import shutil
    import tempfile
    from PIL import Image as PILImage
    from scripts.characters import split_into_scenes, render_scene_frame, W as CHAR_W, H as CHAR_H

    fps = 15
    total_frames = int(audio_duration * fps)
    log.info(f"Rendering {total_frames} character frames at {fps}fps (temp files)...")

    tmp_dir = tempfile.mkdtemp(prefix="charframes_")
    try:
        scenes = split_into_scenes(script)
        n_scenes = len(scenes)
        scene_duration = audio_duration / n_scenes if n_scenes > 0 else audio_duration

        for frame_idx in range(total_frames):
            t = frame_idx / fps
            scene_idx = min(int(t / scene_duration), n_scenes - 1)
            scene = scenes[scene_idx]
            local_t = t - scene_idx * scene_duration

            frame = render_scene_frame(scene, local_t, scene_duration)

            bg = PILImage.new("RGB", (CHAR_W, CHAR_H), (10, 10, 21))
            bg.paste(frame, (0, 0), frame)

            bg.save(os.path.join(tmp_dir, f"frame_{frame_idx:05d}.jpg"), "JPEG", quality=85)

            if frame_idx % (fps * 10) == 0 and frame_idx > 0:
                log.info(f"  Characters: frame {frame_idx}/{total_frames}")

        log.info(f"All {total_frames} frames saved. Encoding with FFmpeg...")

        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", os.path.join(tmp_dir, "frame_%05d.jpg"),
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
            "-pix_fmt", "yuv420p",
            "-t", str(audio_duration + 0.5),
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            size_kb = os.path.getsize(output_path) / 1024
            log.info(f"Character animation saved: {output_path} ({size_kb:.0f} KB)")
        else:
            log.warning(f"Character FFmpeg encode failed (rc={result.returncode}): {result.stderr[:300]}")
            _generate_animated_bg(output_path, audio_duration + 1)

    except Exception as e:
        log.error(f"Character render failed: {e}")
        _generate_animated_bg(output_path, audio_duration + 1)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════
#  MAIN VIDEO COMPOSITION
# ══════════════════════════════════════════════════════════════════

def generate_video(script_data: dict, audio_path: str, output_dir: str) -> str:
    """
    Generate viral short video:
    1. Create background (stock footage OR gameplay loop OR character animation)
    2. Burn ASS karaoke subtitles
    3. Add audio
    NO intro clip — the thumbnail image is the YouTube cover only.
    """
    from scripts.stock_footage import get_stock_for_script, concatenate_clips

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

    # Choose mode: stock (40%), gameplay (35%), characters (25%)
    mode = random.choices(
        ["stock", "gameplay", "characters"],
        weights=[40, 35, 25],
        k=1
    )[0]
    log.info(f"Video mode: {mode}")

    script_text = script_data.get("script", "")
    bg_path = os.path.join(work_dir, f"{base}_bg.mp4")
    stock_clips = []

    # Step 1: Create background — ALWAYS guarantee visible video
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
            log.info("Stock footage unavailable, trying gameplay")
            mode = "gameplay"

    if mode == "gameplay":
        _generate_gameplay_bg(bg_path, audio_duration + 1)
        if not os.path.exists(bg_path) or os.path.getsize(bg_path) < 1000:
            log.warning("Gameplay bg invalid, using animated fallback")
            mode = "fallback"

    if mode == "characters":
        _generate_character_bg(script_text, audio_duration, bg_path)
        if not os.path.exists(bg_path) or os.path.getsize(bg_path) < 1000:
            log.warning("Character bg invalid, using animated fallback")
            mode = "fallback"

    if mode == "fallback":
        _generate_animated_bg(bg_path, audio_duration + 1)

    # Verify background video exists and is valid
    if not os.path.exists(bg_path) or os.path.getsize(bg_path) < 1000:
        log.error(f"Background video missing or too small: {bg_path}")
        return ""

    # Step 2: Generate thumbnail image (for YouTube cover only — NOT in video)
    generate_thumbnail(script_data, thumb_path)
    script_data["thumbnail_path"] = thumb_path

    # Step 3: Generate ASS subtitles
    ass_path = os.path.join(work_dir, f"{base}.ass")
    generate_ass_subtitles(script_text, audio_duration, ass_path)

    # Step 4: Composite final video (background + subtitles + audio)
    log.info("Compositing final video...")

    cmd = [
        "ffmpeg", "-y",
        "-i", bg_path,
        "-i", audio_path,
        "-filter_complex",
        f"[0:v]ass={ass_path}[final]",
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

    if result.returncode != 0:
        log.error(f"FFmpeg failed: {result.stderr[:500]}")
        cmd_simple = [
            "ffmpeg", "-y",
            "-i", bg_path,
            "-i", audio_path,
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-shortest", "-movflags", "+faststart",
            video_path
        ]
        result2 = subprocess.run(cmd_simple, capture_output=True, text=True, timeout=120)
        if result2.returncode != 0:
            log.error(f"Simple fallback also failed: {result2.stderr[:300]}")
            return ""

    size_mb = os.path.getsize(video_path) / (1024 * 1024)
    log.info(f"Video done: {video_path} ({size_mb:.1f} MB)")

    # Cleanup intermediate files
    for f in stock_clips + [bg_path]:
        try:
            if f and os.path.exists(f) and f != video_path:
                os.remove(f)
        except OSError:
            pass

    return video_path
