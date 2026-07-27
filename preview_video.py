#!/usr/bin/env python3
"""
MindRank — Preview v5 (VIRAL TIER)
Multi-clip cuts + text overlays + SFX + music + synced subs
Now with unique scripts per topic!
"""

import os, sys, time, random, re, math, logging, subprocess, tempfile, shutil
from PIL import Image as PILImage, ImageDraw, ImageFont

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

FFMPEG = "/Users/pedrosottomayor/Library/Python/3.9/lib/python/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1"
if not os.path.exists(FFMPEG):
    FFMPEG = "ffmpeg"
BASE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE, "assets")


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
    return [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith((".mp3",))]


def list_sfx():
    d = os.path.join(ASSETS, "sfx")
    if not os.path.exists(d):
        return {}
    return {f.replace(".mp3", ""): os.path.join(d, f)
            for f in sorted(os.listdir(d)) if f.endswith(".mp3")}


def get_duration(path):
    try:
        r = subprocess.run([FFMPEG, "-i", path, "-f", "null", "-"], capture_output=True, text=True, timeout=10)
        m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", r.stderr)
        if m:
            return float(m.group(1)) * 3600 + float(m.group(2)) * 60 + float(m.group(3))
    except:
        pass
    return 25.0


# ══════════════════════════════════════════════════════════════════
#  COLOR SCHEMES PER CATEGORY — visual variety
# ══════════════════════════════════════════════════════════════════

CATEGORY_COLORS = {
    "brain": {"accent": (0, 212, 255), "bg": (10, 10, 30), "glow": (0, 150, 255)},
    "psychology": {"accent": (123, 47, 187), "bg": (15, 5, 25), "glow": (150, 50, 200)},
    "manipulation": {"accent": (255, 50, 50), "bg": (20, 5, 10), "glow": (200, 30, 30)},
    "anxiety": {"accent": (255, 180, 0), "bg": (15, 12, 5), "glow": (200, 150, 0)},
    "habit": {"accent": (80, 220, 120), "bg": (5, 15, 10), "glow": (50, 180, 80)},
    "relationship": {"accent": (255, 100, 150), "bg": (20, 5, 15), "glow": (200, 80, 120)},
    "success": {"accent": (255, 220, 0), "bg": (15, 12, 5), "glow": (200, 180, 0)},
    "fear": {"accent": (180, 50, 50), "bg": (15, 5, 5), "glow": (150, 30, 30)},
    "social": {"accent": (0, 200, 200), "bg": (5, 15, 15), "glow": (0, 150, 150)},
    "emotion": {"accent": (200, 100, 255), "bg": (15, 5, 20), "glow": (150, 80, 200)},
    "decision": {"accent": (100, 200, 255), "bg": (5, 10, 20), "glow": (80, 150, 200)},
    "identity": {"accent": (255, 150, 50), "bg": (15, 10, 5), "glow": (200, 120, 30)},
    "sleep": {"accent": (100, 100, 200), "bg": (5, 5, 15), "glow": (80, 80, 150)},
    "memory": {"accent": (150, 200, 100), "bg": (8, 12, 5), "glow": (100, 150, 60)},
    "creativity": {"accent": (255, 120, 200), "bg": (15, 5, 15), "glow": (200, 80, 150)},
    "motivation": {"accent": (255, 200, 0), "bg": (15, 12, 0), "glow": (200, 160, 0)},
    "truth": {"accent": (200, 200, 200), "bg": (10, 10, 10), "glow": (150, 150, 150)},
    "default": {"accent": (0, 212, 255), "bg": (10, 10, 30), "glow": (0, 150, 255)},
}


def get_category_colors(topic):
    topic_lower = topic.lower()
    for category, colors in CATEGORY_COLORS.items():
        if category in topic_lower:
            return colors
    return CATEGORY_COLORS["default"]


# ══════════════════════════════════════════════════════════════════
#  MULTI-CLIP BACKGROUND — cuts between different clips
# ══════════════════════════════════════════════════════════════════

def build_multiclip_bg(duration, output_path):
    """Cut between 3-5 different stock clips every 3-5 seconds."""
    clips = list_clips("gameplay")
    if len(clips) < 2:
        if clips:
            cmd = [FFMPEG, "-y", "-stream_loop", "-1", "-i", clips[0],
                   "-t", str(duration + 1), "-c:v", "libx264", "-preset", "fast",
                   "-crf", "23", "-an", "-pix_fmt", "yuv420p", output_path]
            subprocess.run(cmd, capture_output=True, timeout=120)
            return os.path.exists(output_path)
        return False

    random.shuffle(clips)
    cut_points = []
    t = 0
    while t < duration + 2:
        cut_dur = random.uniform(3.0, 5.0)
        cut_points.append((t, min(t + cut_dur, duration + 2)))
        t += cut_dur

    seg_dir = tempfile.mkdtemp(prefix="segs_")
    seg_files = []
    for i, (start, end) in enumerate(cut_points):
        clip = clips[i % len(clips)]
        seg_path = os.path.join(seg_dir, f"seg_{i:03d}.mp4")
        seg_dur = end - start
        cmd = [
            FFMPEG, "-y", "-ss", str(start), "-i", clip,
            "-t", str(seg_dur),
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-an", "-pix_fmt", "yuv420p", "-r", "30",
            seg_path
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and os.path.exists(seg_path) and os.path.getsize(seg_path) > 1000:
            seg_files.append(seg_path)
        else:
            cmd2 = [
                FFMPEG, "-y", "-stream_loop", "-1", "-i", clip,
                "-ss", "0", "-t", str(seg_dur),
                "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-an", "-pix_fmt", "yuv420p", "-r", "30",
                seg_path
            ]
            r2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=30)
            if r2.returncode == 0 and os.path.exists(seg_path):
                seg_files.append(seg_path)

    if not seg_files:
        shutil.rmtree(seg_dir, ignore_errors=True)
        return False

    concat_file = os.path.join(seg_dir, "concat.txt")
    with open(concat_file, "w") as f:
        for sf in seg_files:
            f.write(f"file '{sf}'\n")

    cmd = [
        FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-t", str(duration + 1),
        output_path
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    shutil.rmtree(seg_dir, ignore_errors=True)

    if r.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 5000:
        log.info(f"Multi-clip: {len(seg_files)} segments")
        return True
    return False


# ══════════════════════════════════════════════════════════════════
#  TEXT OVERLAYS — key words that pop on screen
# ══════════════════════════════════════════════════════════════════

def extract_key_words(script, n=3):
    skip = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "shall", "can", "need", "dare", "ought",
            "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "above", "below",
            "between", "out", "off", "over", "under", "again", "further", "then",
            "once", "here", "there", "when", "where", "why", "how", "all", "both",
            "each", "few", "more", "most", "other", "some", "such", "no", "nor",
            "not", "only", "own", "same", "so", "than", "too", "very", "just",
            "but", "and", "or", "if", "while", "that", "this", "it", "its",
            "you", "your", "yourself", "i", "me", "my", "we", "our", "they",
            "them", "their", "what", "which", "who", "whom", "these", "those"}
    words = script.split()
    scored = []
    for i, w in enumerate(words):
        clean = w.strip(".,!?;:'\"").lower()
        if clean in skip or len(clean) < 4:
            continue
        pos_score = max(0, 1.0 - i / 30)
        len_score = min(1.0, len(clean) / 8)
        scored.append((clean, pos_score + len_score))
    scored.sort(key=lambda x: -x[1])
    return [w for w, _ in scored[:n]]


def add_text_overlays_to_video(bg_path, script, duration, output_path, colors):
    """Add animated text overlays at key moments using ffmpeg drawtext."""
    keywords = extract_key_words(script, n=3)
    if not keywords:
        shutil.copy2(bg_path, output_path)
        return

    accent = colors["accent"]
    hex_color = f"0x{accent[0]:02x}{accent[1]:02x}{accent[2]:02x}"

    positions = [
        (duration * 0.15, 0.15),
        (duration * 0.45, 0.12),
        (duration * 0.75, 0.10),
    ]

    filters = []
    for i, (kw, (start_t, show_dur)) in enumerate(zip(keywords, positions)):
        end_t = start_t + show_dur
        font_size = 80
        escape_kw = kw.replace("'", "'\\''").replace(":", "\\:")
        dt = (
            f"drawtext=text='{escape_kw}':"
            f"fontsize={font_size}:"
            f"fontcolor={hex_color}:"
            f"borderw=4:"
            f"bordercolor=black:"
            f"x=(w-text_w)/2:"
            f"y=(h-text_h)/2-100:"
            f"enable='between(t,{start_t:.2f},{end_t:.2f})':"
            f"alpha='if(between(t,{start_t:.2f},{start_t + 0.1:.2f}),(t-{start_t:.2f})/0.1,if(between(t,{end_t - 0.1:.2f},{end_t:.2f}),({end_t:.2f}-t)/0.1,1))'"
        )
        filters.append(dt)

    if not filters:
        shutil.copy2(bg_path, output_path)
        return

    vf = ",".join(filters)
    cmd = [
        FFMPEG, "-y", "-i", bg_path,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-an",
        output_path
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        log.warning(f"Text overlay failed: {r.stderr[:200]}")
        shutil.copy2(bg_path, output_path)


# ══════════════════════════════════════════════════════════════════
#  AUDIO MIXING — voice + music + SFX
# ══════════════════════════════════════════════════════════════════

def add_sound_effects(audio_path, duration, output_path):
    music_files = list_music()
    sfx = list_sfx()

    inputs = ["-i", audio_path]
    filter_parts = []
    amix_inputs = ["[0:a]"]

    if music_files:
        music = random.choice(music_files)
        inputs.extend(["-stream_loop", "-1", "-i", music])
        filter_parts.append(f"[1:a]volume=0.10[music]")
        amix_inputs.append("[music]")

    sfx_idx = len(amix_inputs)
    whoosh_times = [4, 8, 12, 16, 20]
    sfx_names = ["whoosh", "pop", "ding", "whoosh", "impact"]
    for i, (st, name) in enumerate(zip(whoosh_times, sfx_names)):
        if st >= duration:
            break
        if name in sfx:
            inputs.extend(["-i", sfx[name]])
            idx = sfx_idx + i
            filter_parts.append(f"[{idx}:a]volume=0.3,adelay={int(st*1000)}|{int(st*1000)}[sfx{i}]")
            amix_inputs.append(f"[sfx{i}]")

    n_inputs = len(amix_inputs)
    mix = f"{''.join(amix_inputs)}amix=inputs={n_inputs}:duration=first:dropout_transition=2[out]"
    full_filter = ";".join(filter_parts + [mix]) if filter_parts else f"[0:a]copy[out]"

    cmd = [FFMPEG, "-y"] + inputs + [
        "-filter_complex", full_filter,
        "-map", "[out]",
        "-c:a", "libmp3lame", "-b:a", "128k",
        "-t", str(duration),
        output_path
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        log.warning(f"SFX mix failed: {r.stderr[:200]}")
        shutil.copy2(audio_path, output_path)


# ══════════════════════════════════════════════════════════════════
#  THUMBNAIL — category-specific colors
# ══════════════════════════════════════════════════════════════════

def generate_thumbnail(title, output_path, colors):
    W, H = 1280, 720
    accent = colors["accent"]
    bg = colors["bg"]
    glow = colors["glow"]

    img = PILImage.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    for y in range(H):
        r = int(bg[0] + 40 * math.sin(y / H * 3.5))
        g = int(bg[1] + 8 * (y / H))
        b = int(bg[2] + 60 * (1 - y / H))
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    for _ in range(10):
        cx = random.randint(-50, W + 50)
        cy = random.randint(-50, H + 50)
        radius = random.randint(80, 200)
        for i in range(radius, 0, -4):
            a = int(50 * (1 - i / radius) ** 2)
            if a < 1: continue
            draw.ellipse([cx - i, cy - i, cx + i, cy + i], fill=accent)

    fcx, fcy, fr = 180, 360, 90
    draw.ellipse([fcx - fr, fcy - fr, fcx + fr, fcy + fr], fill=(220, 180, 150))
    ey = fcy - 20
    for ex in [fcx - 28, fcx + 28]:
        draw.ellipse([ex - 18, ey - 16, ex + 18, ey + 16], fill=(255, 255, 255))
        draw.ellipse([ex - 9, ey - 9, ex + 9, ey + 9], fill=(20, 20, 30))
    draw.ellipse([fcx - 20, fcy + 21, fcx + 20, fcy + 53], fill=(150, 50, 50))
    draw.line([fcx - 40, ey - 30, fcx - 8, ey - 24], fill=(80, 50, 30), width=5)
    draw.line([fcx + 8, ey - 24, fcx + 40, ey - 30], fill=(80, 50, 30), width=5)
    draw.polygon([(300, 360), (370, 330), (370, 390)], fill=accent)

    clean = title.upper()
    for p in ["WHY:", "SECRET:", "DARK TRUTH:", "SHOCKING:"]:
        if clean.startswith(p):
            clean = clean[len(p):].strip()
            break
    font = get_font(88, bold=True)
    lines, line = [], ""
    for w in clean.split():
        test = (line + " " + w).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > 700:
            lines.append(line)
            line = w
        else:
            line = test
    if line:
        lines.append(line)
    ty = (H - len(lines) * 100) // 2
    for ln in lines[:3]:
        bbox = draw.textbbox((0, 0), ln, font=font)
        tx = max(400, (W - (bbox[2] - bbox[0])) // 2)
        for dx in range(-4, 5):
            for dy in range(-4, 5):
                draw.text((tx + dx, ty + dy), ln, font=font, fill=(0, 0, 0))
        draw.text((tx, ty), ln, font=font, fill=accent)
        ty += 100
    draw.text((20, 18), "MindRank", font=get_font(28, bold=True), fill=accent)
    img.save(output_path, "JPEG", quality=95)


# ══════════════════════════════════════════════════════════════════
#  SUBTITLES
# ══════════════════════════════════════════════════════════════════

def parse_srt(path):
    ts = []
    try:
        with open(path) as f:
            content = f.read()
        for block in re.split(r"\n\n+", content.strip()):
            lines = block.strip().split("\n")
            if len(lines) < 3: continue
            m = re.match(r"(\d{2}):(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[.,](\d{3})", lines[1])
            if not m: continue
            g = m.groups()
            s = int(g[0])*3600+int(g[1])*60+int(g[2])+int(g[3])/1000
            e = int(g[4])*3600+int(g[5])*60+int(g[6])+int(g[7])/1000
            t = " ".join(lines[2:]).strip()
            if t: ts.append({"start": s, "end": e, "text": t})
    except: pass
    return ts


def fmt_t(s):
    return f"{int(s//3600)}:{int((s%3600)//60):02d}:{int(s%60):02d}.{int((s%1)*100):02d}"


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  MindRank — Preview v5 (VIRAL TIER)")
    print("  Unique scripts + multi-clip + SFX + music")
    print("=" * 60)

    out = os.path.join(BASE, "output")
    os.makedirs(out, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    base = f"preview_{ts}"

    # 1. Script (now unique per topic!)
    print("\n[1/7] Script (unique per topic)...")
    sys.path.insert(0, BASE)
    from scripts.generate_script import generate_script_offline
    topics = [
        "The dark psychology trick that works every time",
        "Top 5 signs you are a genius but don t know it",
        "5 cognitive biases that control your decisions",
        "The friendship formula that psychology discovered",
        "Why high IQ people are actually lonelier",
    ]
    topic = random.choice(topics)
    sd = generate_script_offline(topic)
    print(f"  Topic: {topic}")
    print(f"  Title: {sd['title']}")
    print(f"  Hook: {sd['hook'][:60]}...")
    print(f"  Words: {len(sd['script'].split())}")

    # Get category colors
    colors = get_category_colors(topic)
    print(f"  Colors: accent={colors['accent']}")

    # 2. Voiceover
    print("\n[2/7] Voiceover...")
    import asyncio, edge_tts
    voice_raw = os.path.join(out, f"{base}_voice.mp3")

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
        srt = voice_raw.replace("_voice.mp3", ".srt")
        s = sm.get_srt()
        if s:
            with open(srt, "w") as f:
                f.write(s)
    asyncio.run(gen())
    dur = get_duration(voice_raw)
    print(f"  Duration: {dur:.1f}s")

    # 3. Multi-clip background
    print("\n[3/7] Multi-clip background...")
    bg_raw = os.path.join(out, f"{base}_bg_raw.mp4")
    ok = build_multiclip_bg(dur + 1, bg_raw)
    if not ok:
        print("  Fallback: single clip")
        clips = list_clips("gameplay")
        if clips:
            cmd = [FFMPEG, "-y", "-stream_loop", "-1", "-i", random.choice(clips),
                   "-t", str(dur+1), "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                   "-an", "-pix_fmt", "yuv420p", bg_raw]
            subprocess.run(cmd, capture_output=True, timeout=120)

    # 4. Text overlays (with category colors!)
    print("\n[4/7] Text overlays...")
    bg_text = os.path.join(out, f"{base}_bg_text.mp4")
    add_text_overlays_to_video(bg_raw, sd["script"], dur, bg_text, colors)
    if not os.path.exists(bg_text) or os.path.getsize(bg_text) < 5000:
        bg_text = bg_raw

    # 5. Audio
    print("\n[5/7] Mixing audio...")
    audio = os.path.join(out, f"{base}_audio.mp3")
    add_sound_effects(voice_raw, dur, audio)

    # 6. Subtitles
    print("\n[6/7] Subtitles...")
    srt_path = voice_raw.replace("_voice.mp3", ".srt")
    timestamps = parse_srt(srt_path)
    words = sd["script"].split()
    chunks = []
    if timestamps and len(timestamps) >= 2:
        for ts in timestamps:
            sw = ts["text"].split()
            d = ts["end"] - ts["start"]
            if d <= 0: continue
            csz = max(2, min(4, len(sw) // 2))
            for i in range(0, len(sw), csz):
                cw = sw[i:i+csz]
                p = i / max(1, len(sw))
                chunks.append({"text": " ".join(cw), "start": ts["start"]+p*d,
                              "end": ts["start"]+min(1.0,(i+csz)/max(1,len(sw)))*d})
    else:
        wps = len(words)/dur if dur>0 else 3
        csz = max(2, min(5, int(wps*1.2)))
        for i in range(0, len(words), csz):
            cw = words[i:i+csz]
            chunks.append({"text": " ".join(cw), "start": i*(dur/len(words)),
                          "end": min((i+csz)*(dur/len(words)), dur)})

    header = "[Script Info]\nTitle: MindRank\nScriptType: v4.00+\nWrapStyle: 0\nScaledBorderAndShadow: yes\nPlayResX: 1080\nPlayResY: 1920\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Arial Black,72,&H00FFFFFF,&H000000FF,&H00000000,&H96000000,-1,0,0,0,100,100,1,0,1,4,2,2,50,50,580,1\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    events = []
    for c in chunks:
        st, et = fmt_t(c["start"]), fmt_t(c["end"])
        ws = c["text"].split()
        if not ws: continue
        cd = c["end"] - c["start"]
        kp = " ".join(f"{{\\kf{int(cd*100/len(ws))}}}{w}" for w in ws)
        events.append(f"Dialogue: 0,{st},{et},Default,,0,0,0,,{kp}")

    ass = os.path.join(out, f"{base}.ass")
    with open(ass, "w") as f:
        f.write(header + "\n".join(events) + "\n")
    print(f"  {len(chunks)} chunks")

    # 7. Composite
    print("\n[7/7] Final composite...")
    final = os.path.join(out, f"{base}.mp4")
    cmd = [FFMPEG, "-y", "-i", bg_text, "-i", audio,
           "-filter_complex", f"[0:v]ass={ass}[final]",
           "-map", "[final]", "-map", "1:a",
           "-c:v", "libx264", "-preset", "medium", "-crf", "22",
           "-c:a", "aac", "-b:a", "128k",
           "-pix_fmt", "yuv420p", "-shortest", "-movflags", "+faststart", final]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        cmd2 = [FFMPEG, "-y", "-i", bg_text, "-i", audio,
                "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                "-shortest", "-movflags", "+faststart", final]
        subprocess.run(cmd2, capture_output=True, timeout=120)

    # Thumbnail
    thumb = os.path.join(out, f"{base}_thumb.jpg")
    generate_thumbnail(sd["title"], thumb, colors)

    if os.path.exists(final):
        size_mb = os.path.getsize(final) / (1024*1024)
        print(f"\n{'='*60}")
        print(f"  VIDEO: {final}")
        print(f"  THUMB: {thumb}")
        print(f"  Title: {sd['title']}")
        print(f"  Topic: {topic}")
        print(f"  Duration: {dur:.1f}s | Size: {size_mb:.1f} MB")
        print(f"  Multi-clip + text overlays + SFX + music + category colors")
        print(f"{'='*60}")
    else:
        print("  ERROR")


if __name__ == "__main__":
    main()
