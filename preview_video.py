#!/usr/bin/env python3
"""
MindRank — Preview v4
Real footage + enthusiastic voice + synced subtitles + background music + thumbnail
"""

import os, sys, time, random, re, math, logging, subprocess, tempfile, shutil
from PIL import Image as PILImage, ImageDraw, ImageFont

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

FFMPEG = "/Users/pedrosottomayor/Library/Python/3.9/lib/python/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1"
if not os.path.exists(FFMPEG):
    FFMPEG = "ffmpeg"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE_DIR, "assets")


def get_font(size, bold=False):
    for f in ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc"]:
        try:
            return ImageFont.truetype(f, size)
        except:
            continue
    return ImageFont.load_default()


def list_clips(subdir):
    d = os.path.join(ASSETS, subdir)
    if not os.path.exists(d):
        return []
    return [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith(".mp4")]


def list_music():
    d = os.path.join(ASSETS, "music")
    if not os.path.exists(d):
        return []
    return [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith((".mp3", ".wav", ".ogg"))]


def get_duration(path):
    try:
        r = subprocess.run([FFMPEG, "-i", path, "-f", "null", "-"], capture_output=True, text=True, timeout=10)
        m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", r.stderr)
        if m:
            return float(m.group(1)) * 3600 + float(m.group(2)) * 60 + float(m.group(3))
    except:
        pass
    return 25.0


def pick_background(duration):
    clips = list_clips("gameplay")
    if not clips:
        return None
    chosen = random.choice(clips)
    log.info(f"Background: {os.path.basename(chosen)}")
    tmp = tempfile.mktemp(suffix=".mp4")
    cmd = [FFMPEG, "-y", "-stream_loop", "-1", "-i", chosen,
           "-t", str(duration + 1), "-c:v", "libx264", "-preset", "fast",
           "-crf", "23", "-an", "-pix_fmt", "yuv420p", tmp]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode == 0 and os.path.exists(tmp) and os.path.getsize(tmp) > 5000:
        return tmp
    return None


def mix_music(voice_path, duration, output_path):
    """Mix voice with background music at low volume."""
    music_files = list_music()
    if not music_files:
        # Just copy voice as-is
        shutil.copy2(voice_path, output_path)
        return

    music = random.choice(music_files)
    log.info(f"Music: {os.path.basename(music)}")

    # Mix: voice at full volume, music at 12% volume, loop music to match duration
    cmd = [
        FFMPEG, "-y",
        "-i", voice_path,
        "-stream_loop", "-1", "-i", music,
        "-filter_complex",
        f"[1:a]volume=0.12[music];[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[out]",
        "-map", "[out]",
        "-c:a", "libmp3lame", "-b:a", "128k",
        "-t", str(duration),
        output_path
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        log.warning(f"Music mix failed, using voice only: {r.stderr[:200]}")
        shutil.copy2(voice_path, output_path)


def parse_srt(path):
    ts = []
    try:
        with open(path) as f:
            content = f.read()
        for block in re.split(r"\n\n+", content.strip()):
            lines = block.strip().split("\n")
            if len(lines) < 3:
                continue
            m = re.match(r"(\d{2}):(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[.,](\d{3})", lines[1])
            if not m:
                continue
            g = m.groups()
            s = int(g[0]) * 3600 + int(g[1]) * 60 + int(g[2]) + int(g[3]) / 1000
            e = int(g[4]) * 3600 + int(g[5]) * 60 + int(g[6]) + int(g[7]) / 1000
            t = " ".join(lines[2:]).strip()
            if t:
                ts.append({"start": s, "end": e, "text": t})
    except:
        pass
    return ts


def fmt_t(s):
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = int(s % 60)
    cs = int((s % 1) * 100)
    return f"{h}:{m:02d}:{sec:02d}.{cs:02d}"


def generate_thumbnail(title, output_path):
    """Generate clickbait thumbnail: shocked face + yellow arrow + huge text."""
    W, H = 1280, 720
    img = PILImage.new("RGB", (W, H), (5, 5, 12))
    draw = ImageDraw.Draw(img)

    # Dramatic gradient
    for y in range(H):
        r = int(8 + 40 * math.sin(y / H * 3.5))
        g = int(2 + 8 * (y / H))
        b = int(18 + 60 * (1 - y / H))
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Glowing orbs
    for _ in range(10):
        cx = random.randint(-50, W + 50)
        cy = random.randint(-50, H + 50)
        radius = random.randint(80, 200)
        color = random.choice([(0, 212, 255), (123, 47, 187), (255, 50, 50), (255, 220, 0)])
        for i in range(radius, 0, -4):
            a = int(50 * (1 - i / radius) ** 2)
            if a < 1:
                continue
            draw.ellipse([cx - i, cy - i, cx + i, cy + i], fill=color)

    # Shocked face
    fcx, fcy = 180, 360
    fr = 90
    draw.ellipse([fcx - fr, fcy - fr, fcx + fr, fcy + fr], fill=(220, 180, 150))
    # Eyes
    ey = fcy - 20
    for ex in [fcx - 28, fcx + 28]:
        draw.ellipse([ex - 18, ey - 16, ex + 18, ey + 16], fill=(255, 255, 255))
        draw.ellipse([ex - 9, ey - 9, ex + 9, ey + 9], fill=(20, 20, 30))
        draw.ellipse([ex + 2, ey - 6, ex + 7, ey - 1], fill=(255, 255, 255))
    # Mouth
    my = fcy + 35
    draw.ellipse([fcx - 20, my - 14, fcx + 20, my + 18], fill=(150, 50, 50))
    # Eyebrows
    draw.line([fcx - 40, ey - 30, fcx - 8, ey - 24], fill=(80, 50, 30), width=5)
    draw.line([fcx + 8, ey - 24, fcx + 40, ey - 30], fill=(80, 50, 30), width=5)

    # Yellow arrow
    draw.polygon([(300, 360), (370, 330), (370, 390)], fill=(255, 220, 0))

    # Big text
    clean = title.upper()
    for prefix in ["WHY:", "SECRET:", "DARK TRUTH:", "SHOCKING:", "HIDDEN:"]:
        if clean.startswith(prefix):
            clean = clean[len(prefix):].strip()
            break
    font = get_font(88, bold=True)
    lines = []
    words = clean.split()
    line = ""
    for w in words:
        test = (line + " " + w).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > 700:
            lines.append(line)
            line = w
        else:
            line = test
    if line:
        lines.append(line)

    total_h = len(lines) * 100
    ty = (H - total_h) // 2
    for line in lines[:3]:
        bbox = draw.textbbox((0, 0), line, font=font)
        tx = max(400, (W - (bbox[2] - bbox[0])) // 2)
        # Shadow
        for dx in range(-4, 5):
            for dy in range(-4, 5):
                draw.text((tx + dx, ty + dy), line, font=font, fill=(0, 0, 0))
        draw.text((tx, ty), line, font=font, fill=(255, 220, 0))
        ty += 100

    # Logo
    logo = get_font(28, bold=True)
    draw.text((20, 18), "MindRank", font=logo, fill=(0, 212, 255))

    img.save(output_path, "JPEG", quality=95)
    log.info(f"Thumbnail: {output_path}")


def main():
    print("=" * 60)
    print("  MindRank — Preview v4")
    print("  Real footage + music + synced subs + thumbnail")
    print("=" * 60)

    out = os.path.join(BASE_DIR, "output")
    os.makedirs(out, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    base = f"preview_{ts}"

    # 1. Script
    print("\n[1/6] Script...")
    sys.path.insert(0, BASE_DIR)
    from scripts.generate_script import generate_script_offline
    topics = [
        "Top 5 signs you are a genius but don't know it",
        "The dark psychology trick that works every time",
        "5 body language secrets that reveal someone's intentions",
        "Why high IQ people are actually lonelier",
        "The psychology behind why we procrastinate",
        "7 signs you are smarter than you think",
        "The manipulation tactic narcissists use on everyone",
        "Why your brain lies to you about danger",
        "The friendship formula that psychology discovered",
        "5 cognitive biases that control your decisions",
    ]
    sd = generate_script_offline(random.choice(topics))
    print(f"  Title: {sd['title']}")
    print(f"  Words: {len(sd['script'].split())}")

    # 2. Voiceover
    print("\n[2/6] Voiceover (AndrewNeural +15%)...")
    import asyncio, edge_tts
    voice_raw = os.path.join(out, f"{base}_voice_raw.mp3")

    async def gen():
        c = edge_tts.Communicate(text=sd["script"], voice="en-US-AndrewNeural", rate="+15%", pitch="+2Hz")
        sm = edge_tts.SubMaker()
        data = b""
        async for ch in c.stream():
            if ch["type"] == "audio":
                data += ch["data"]
            elif ch["type"] == "SentenceBoundary":
                sm.feed(ch)
        with open(voice_raw, "wb") as f:
            f.write(data)
        srt = voice_raw.replace("_voice_raw.mp3", ".srt")
        s = sm.get_srt()
        if s:
            with open(srt, "w") as f:
                f.write(s)

    asyncio.run(gen())
    dur = get_duration(voice_raw)
    print(f"  Duration: {dur:.1f}s")

    # 3. Mix with background music
    print("\n[3/6] Mixing background music...")
    audio = os.path.join(out, f"{base}.mp3")
    mix_music(voice_raw, dur, audio)

    # 4. Background
    print("\n[4/6] Background (real footage)...")
    bg = os.path.join(out, f"{base}_bg.mp4")
    bg_tmp = pick_background(dur + 1)
    if bg_tmp:
        shutil.move(bg_tmp, bg)
        print(f"  Ready: {os.path.basename(bg)}")
    else:
        print("  ERROR: No background")
        return

    # 5. Subtitles
    print("\n[5/6] Subtitles (synced, bottom only)...")
    srt_path = voice_raw.replace("_voice_raw.mp3", ".srt")
    timestamps = parse_srt(srt_path)
    words = sd["script"].split()
    chunks = []
    if timestamps and len(timestamps) >= 2:
        print(f"  {len(timestamps)} real timestamps")
        for ts in timestamps:
            sw = ts["text"].split()
            d = ts["end"] - ts["start"]
            if d <= 0:
                continue
            csz = max(2, min(4, len(sw) // 2))
            for i in range(0, len(sw), csz):
                cw = sw[i:i + csz]
                p = i / max(1, len(sw))
                chunks.append({"text": " ".join(cw), "start": ts["start"] + p * d,
                              "end": ts["start"] + min(1.0, (i + csz) / max(1, len(sw))) * d})
    else:
        wps = len(words) / dur if dur > 0 else 3
        csz = max(2, min(5, int(wps * 1.2)))
        for i in range(0, len(words), csz):
            cw = words[i:i + csz]
            chunks.append({"text": " ".join(cw), "start": i * (dur / len(words)),
                          "end": min((i + csz) * (dur / len(words)), dur)})

    header = "[Script Info]\nTitle: MindRank\nScriptType: v4.00+\nWrapStyle: 0\nScaledBorderAndShadow: yes\nPlayResX: 1080\nPlayResY: 1920\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Arial Black,72,&H00FFFFFF,&H000000FF,&H00000000,&H96000000,-1,0,0,0,100,100,1,0,1,4,2,2,50,50,580,1\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    events = []
    for c in chunks:
        st, et = fmt_t(c["start"]), fmt_t(c["end"])
        ws = c["text"].split()
        if not ws:
            continue
        cd = c["end"] - c["start"]
        kp = " ".join(f"{{\\kf{int(cd * 100 / len(ws))}}}{w}" for w in ws)
        events.append(f"Dialogue: 0,{st},{et},Default,,0,0,0,,{kp}")

    ass = os.path.join(out, f"{base}.ass")
    with open(ass, "w") as f:
        f.write(header + "\n".join(events) + "\n")
    print(f"  {len(chunks)} chunks, bottom only")

    # 6. Composite
    print("\n[6/6] Compositing...")
    final = os.path.join(out, f"{base}.mp4")
    cmd = [FFMPEG, "-y", "-i", bg, "-i", audio,
           "-filter_complex", f"[0:v]ass={ass}[final]",
           "-map", "[final]", "-map", "1:a",
           "-c:v", "libx264", "-preset", "medium", "-crf", "22",
           "-c:a", "aac", "-b:a", "128k",
           "-pix_fmt", "yuv420p", "-shortest", "-movflags", "+faststart", final]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        cmd2 = [FFMPEG, "-y", "-i", bg, "-i", audio,
                "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                "-shortest", "-movflags", "+faststart", final]
        subprocess.run(cmd2, capture_output=True, timeout=120)

    # Thumbnail
    thumb = os.path.join(out, f"{base}_thumb.jpg")
    generate_thumbnail(sd["title"], thumb)

    if os.path.exists(final):
        size_mb = os.path.getsize(final) / (1024 * 1024)
        print(f"\n{'=' * 60}")
        print(f"  VIDEO: {final}")
        print(f"  THUMB: {thumb}")
        print(f"  Title: {sd['title']}")
        print(f"  Duration: {dur:.1f}s | Size: {size_mb:.1f} MB")
        print(f"  Voice: AndrewNeural +15% | Music: lo-fi")
        print(f"  Subtitles: synced, bottom only")
        print(f"  Background: REAL stock footage")
        print(f"{'=' * 60}")
    else:
        print("  ERROR: Composite failed")


if __name__ == "__main__":
    main()
