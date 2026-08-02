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
import shutil
import subprocess
from typing import List, Tuple, Optional

log = logging.getLogger(__name__)

_LOCAL_FFMPEG = "/Users/pedrosottomayor/Library/Python/3.9/lib/python/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1"
FFMPEG = shutil.which("ffmpeg") or _LOCAL_FFMPEG

def _get_duration(path):
    try:
        r = subprocess.run([FFMPEG, "-i", path, "-f", "null", "-"], capture_output=True, text=True, timeout=10)
        m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", r.stderr)
        if m:
            return float(m.group(1))*3600 + float(m.group(2))*60 + float(m.group(3))
    except:
        pass
    return 0

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


def _parse_srt_timestamps(srt_path: str) -> list:
    """Parse SRT file from edge-tts into list of {start, end, text} dicts."""
    import re
    timestamps = []
    try:
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Split by double newline (SRT blocks)
        blocks = re.split(r"\n\n+", content.strip())
        for block in blocks:
            lines = block.strip().split("\n")
            if len(lines) < 3:
                continue
            # Line 2: timestamps
            time_match = re.match(
                r"(\d{2}):(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[.,](\d{3})",
                lines[1]
            )
            if not time_match:
                continue
            g = time_match.groups()
            start = int(g[0]) * 3600 + int(g[1]) * 60 + int(g[2]) + int(g[3]) / 1000
            end = int(g[4]) * 3600 + int(g[5]) * 60 + int(g[6]) + int(g[7]) / 1000
            text = " ".join(lines[2:]).strip()
            if text:
                timestamps.append({"start": start, "end": end, "text": text})
    except Exception as e:
        log.warning(f"Failed to parse SRT: {e}")
    return timestamps


def _build_chunks_from_timestamps(timestamps: list, all_words: list, audio_duration: float) -> list:
    """Build subtitle chunks using real edge-tts sentence timestamps."""
    chunks = []
    word_idx = 0

    for ts in timestamps:
        sentence_words = ts["text"].split()
        sentence_dur = ts["end"] - ts["start"]
        if sentence_dur <= 0:
            continue

        # Split sentence into 2-4 word chunks for karaoke effect
        chunk_size = max(2, min(4, len(sentence_words) // 2))
        for i in range(0, len(sentence_words), chunk_size):
            cw = sentence_words[i:i + chunk_size]
            progress = i / max(1, len(sentence_words))
            chunk_start = ts["start"] + progress * sentence_dur
            chunk_end = ts["start"] + min(1.0, (i + chunk_size) / max(1, len(sentence_words))) * sentence_dur
            chunks.append({
                "text": " ".join(cw),
                "start": chunk_start,
                "end": chunk_end,
            })

    # Fill any gap at the end
    if chunks and chunks[-1]["end"] < audio_duration - 0.5:
        chunks.append({
            "text": "...",
            "start": chunks[-1]["end"],
            "end": audio_duration,
        })

    return chunks if chunks else [{"text": " ".join(all_words), "start": 0, "end": audio_duration}]


def generate_ass_subtitles(script: str, audio_duration: float, output_path: str, srt_path: str = None):
    """Generate ASS subtitles using edge-tts timestamps when available, with BigWord emphasis."""
    # Try to load real timestamps from edge-tts SRT
    real_timestamps = []
    if srt_path and os.path.exists(srt_path):
        real_timestamps = _parse_srt_timestamps(srt_path)

    words = script.split()
    if not words:
        return

    if real_timestamps and len(real_timestamps) >= 3:
        log.info(f"Using {len(real_timestamps)} real timestamps from edge-tts")
        chunks = _build_chunks_from_timestamps(real_timestamps, words, audio_duration)
    else:
        log.info("No real timestamps, estimating from word count")
        words_per_sec = len(words) / audio_duration if audio_duration > 0 else 3.0
        chunk_size = max(2, min(5, int(words_per_sec * 1.2)))
        chunks = []
        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i + chunk_size]
            chunks.append({
                "text": " ".join(chunk_words),
                "start": i * (audio_duration / len(words)),
                "end": min((i + chunk_size) * (audio_duration / len(words)), audio_duration),
            })

    n_chunks = len(chunks)

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
Style: Default,Arial Black,72,&H00FFFFFF,&H000000FF,&H00000000,&H96000000,-1,0,0,0,100,100,1,0,1,4,2,2,50,50,580,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events = []
    for i, chunk in enumerate(chunks):
        start = chunk["start"]
        end = chunk["end"]
        start_t = _format_ass_time(start)
        end_t = _format_ass_time(end)

        words_in_chunk = chunk["text"].split()
        if not words_in_chunk:
            continue

        chunk_dur = end - start
        karaoke_parts = []
        for w in words_in_chunk:
            w_dur = int(chunk_dur * 100 / len(words_in_chunk))
            karaoke_parts.append(f"{{\\kf{w_dur}}}{w}")
        karaoke_text = " ".join(karaoke_parts)

        # Only bottom karaoke subtitles — no BigWord at top
        events.append(
            f"Dialogue: 0,{start_t},{end_t},Default,,0,0,0,,{karaoke_text}"
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
        FFMPEG, "-y",
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
            FFMPEG, "-y", "-f", "lavfi", "-i",
            f"color=c=0x0A0A15:s={WIDTH}x{HEIGHT}:d={duration}:r={FPS}",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            output_path
        ], capture_output=True, timeout=60)


# ══════════════════════════════════════════════════════════════════
#  GAMEPLAY BACKGROUND — Real gameplay clips (Subway Surfers, Minecraft,
#  satisfying ASMR) with Ken Burns pan/zoom. Loops to fill the duration.
# ══════════════════════════════════════════════════════════════════

_GAMEPLAY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "gameplay")

def _find_gameplay_clips():
    """Return list of real gameplay clip paths committed to the repo."""
    clips = []
    if os.path.isdir(_GAMEPLAY_DIR):
        for f in sorted(os.listdir(_GAMEPLAY_DIR)):
            if f.startswith("gameplay_") and f.endswith((".mp4", ".webm", ".mov")):
                clips.append(os.path.join(_GAMEPLAY_DIR, f))
    return clips


def _generate_gameplay_bg(output_path: str, duration: float):
    """Create background from a real gameplay clip (loop + pan/zoom).

    Falls back to the animated background if no clips are available.
    """
    clips = _find_gameplay_clips()
    if not clips:
        log.warning("No real gameplay clips found, using animated background")
        _generate_animated_bg(output_path, duration + 1)
        return

    clip_path = random.choice(clips)
    log.info(f"Using real gameplay clip: {os.path.basename(clip_path)} ({duration:.0f}s bg)")

    # Subtle Ken Burns: slow zoom in/out + gentle pan, then crop to 9:16
    filter_chain = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "zoompan=z='1.05+0.04*sin(on/60)':"
        "x='iw/2-(iw/zoom/2)+20*sin(on/45)':"
        "y='ih/2-(ih/zoom/2)+10*cos(on/35)':"
        "d=1:s=1080x1920:fps=30,"
        "format=yuv420p"
    )

    cmd = [
        FFMPEG, "-y",
        "-stream_loop", "-1",
        "-i", clip_path,
        "-t", str(duration),
        "-vf", filter_chain,
        "-c:v", "libx264", "-preset", "fast", "-crf", "24",
        "-pix_fmt", "yuv420p",
        "-an",
        output_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            size_kb = os.path.getsize(output_path) / 1024
            log.info(f"Gameplay background saved: {output_path} ({size_kb:.0f} KB)")
            return
        else:
            log.warning(f"Gameplay clip ffmpeg failed: {result.stderr[:300]}")
    except Exception as e:
        log.warning(f"Gameplay clip error: {e}")

    # Retry with a different clip, then fall back to animated
    for alt in [c for c in clips if c != clip_path]:
        retry_cmd = [
            FFMPEG, "-y",
            "-stream_loop", "-1",
            "-i", alt,
            "-t", str(duration),
            "-vf", filter_chain,
            "-c:v", "libx264", "-preset", "fast", "-crf", "24",
            "-pix_fmt", "yuv420p",
            "-an",
            output_path
        ]
        try:
            result = subprocess.run(retry_cmd, capture_output=True, text=True, timeout=180)
            if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                log.info(f"Gameplay background saved (retry): {output_path}")
                return
        except Exception:
            continue

    log.warning("All gameplay clips failed, using animated background")
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
            FFMPEG, "-y",
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
    audio_duration = _get_duration(audio_path)
    if audio_duration == 0:
        audio_duration = 25.0
    log.info(f"Audio duration: {audio_duration:.1f}s")

    script_text = script_data.get("script", "")
    bg_path = os.path.join(work_dir, f"{base}_bg.mp4")

    # Step 1: Create background — ONLY generated content, NO watermarked clips
    mode = "gameplay"
    log.info(f"Video mode: {mode}")

    _generate_gameplay_bg(bg_path, audio_duration + 1)
    if not os.path.exists(bg_path) or os.path.getsize(bg_path) < 1000:
        log.warning("Gameplay bg invalid, using animated fallback")
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
    srt_path = audio_path.rsplit(".", 1)[0] + ".srt"
    generate_ass_subtitles(script_text, audio_duration, ass_path, srt_path=srt_path)

    # Step 4: Composite final video (background + subtitles + audio)
    log.info("Compositing final video...")

    cmd = [
        FFMPEG, "-y",
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
            FFMPEG, "-y",
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
    try:
        if bg_path and os.path.exists(bg_path) and bg_path != video_path:
            os.remove(bg_path)
    except OSError:
        pass

    return video_path
