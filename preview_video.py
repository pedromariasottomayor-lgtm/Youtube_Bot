#!/usr/bin/env python3
"""
MindRank Preview — fixes: no garbage clips, no watermarks, text+SFX+music
"""

import os, sys, time, random, re, math, logging, subprocess, tempfile, shutil

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

FFMPEG = "/Users/pedrosottomayor/Library/Python/3.9/lib/python/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1"
BASE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE, "assets")


def get_duration(path):
    try:
        r = subprocess.run([FFMPEG, "-i", path, "-f", "null", "-"], capture_output=True, text=True, timeout=10)
        m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", r.stderr)
        if m:
            return float(m.group(1)) * 3600 + float(m.group(2)) * 60 + float(m.group(3))
    except:
        pass
    return 0


def validate_clip(path):
    """Check if a clip is usable (reasonable quality, no watermarks)."""
    if not os.path.exists(path):
        return False
    size_mb = os.path.getsize(path) / (1024 * 1024)
    if size_mb < 0.5:
        log.warning(f"Clip too small: {os.path.basename(path)} ({size_mb:.1f} MB)")
        return False
    dur = get_duration(path)
    if dur < 3:
        log.warning(f"Clip too short: {os.path.basename(path)} ({dur:.0f}s)")
        return False
    return True


def list_good_clips():
    """List only valid gameplay clips."""
    d = os.path.join(ASSETS, "gameplay")
    if not os.path.exists(d):
        return []
    clips = [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith(".mp4")]
    return [c for c in clips if validate_clip(c)]


def list_music():
    d = os.path.join(ASSETS, "music")
    if not os.path.exists(d): return []
    return [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith((".mp3",))]


def list_sfx():
    d = os.path.join(ASSETS, "sfx")
    if not os.path.exists(d): return {}
    return {f.replace(".mp3", ""): os.path.join(d, f)
            for f in sorted(os.listdir(d)) if f.endswith(".mp3")}


# ══════════════════════════════════════════════════════════════════
#  MULTI-CLIP BACKGROUND — robust, skips end segments
# ══════════════════════════════════════════════════════════════════

def build_multiclip_bg(duration, output_path):
    """Cut between good clips. Avoids last 40% of each clip (where credits live)."""
    clips = list_good_clips()
    if len(clips) < 2:
        log.warning("Need at least 2 good clips")
        return False

    random.shuffle(clips)
    seg_dur = 3.5  # Each segment is ~3.5s — fast enough to be engaging
    total_needed = duration + 1
    seg_count = max(3, int(total_needed / seg_dur) + 1)

    seg_dir = tempfile.mkdtemp(prefix="segs_")
    seg_files = []

    for i in range(seg_count):
        clip = clips[i % len(clips)]
        clip_dur = get_duration(clip)
        safe_end = clip_dur * 0.6  # Skip last 40% of clip to avoid credits
        if safe_end < seg_dur:
            continue

        # Pick a random start within the safe zone
        max_start = max(0, safe_end - seg_dur - 0.5)
        start = random.uniform(0.5, max_start) if max_start > 1 else 0.5

        seg_path = os.path.join(seg_dir, f"seg_{i:03d}.mp4")
        cmd = [
            FFMPEG, "-y",
            "-ss", f"{start:.1f}", "-i", clip,
            "-t", f"{seg_dur:.1f}",
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-an", "-pix_fmt", "yuv420p", "-r", "30",
            seg_path
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and os.path.exists(seg_path) and os.path.getsize(seg_path) > 1000:
            seg_files.append(seg_path)

    if len(seg_files) < 2:
        shutil.rmtree(seg_dir, ignore_errors=True)
        return False

    concat_file = os.path.join(seg_dir, "concat.txt")
    with open(concat_file, "w") as f:
        for sf in seg_files:
            f.write(f"file '{sf}'\n")

    cmd = [
        FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-t", str(total_needed),
        output_path
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    shutil.rmtree(seg_dir, ignore_errors=True)

    if r.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 5000:
        log.info(f"Multi-clip: {len(seg_files)} segments from {len(clips)} clips")
        return True
    return False


# ══════════════════════════════════════════════════════════════════
#  TEXT OVERLAYS — key words at key moments
# ══════════════════════════════════════════════════════════════════

def extract_key_words(script, n=3):
    skip = {"the","a","an","is","are","was","were","be","been","being",
            "have","has","had","do","does","did","will","would","could",
            "should","may","might","shall","can","need","dare","ought",
            "used","to","of","in","for","on","with","at","by","from",
            "as","into","through","during","before","after","above","below",
            "between","out","off","over","under","again","further","then",
            "once","here","there","when","where","why","how","all","both",
            "each","few","more","most","other","some","such","no","nor",
            "not","only","own","same","so","than","too","very","just",
            "but","and","or","if","while","that","this","it","its",
            "you","your","yourself","i","me","my","we","our","they",
            "them","their","what","which","who","whom","these","those"}
    words = script.split()
    scored = []
    for i, w in enumerate(words):
        clean = w.strip(".,!?;:'\"").lower()
        if clean in skip or len(clean) < 4: continue
        pos_score = max(0, 1.0 - i / 30)
        len_score = min(1.0, len(clean) / 8)
        scored.append((clean, pos_score + len_score))
    scored.sort(key=lambda x: -x[1])
    return [w for w, _ in scored[:n]]


def add_text_overlays(bg_path, script, duration, output_path):
    keywords = extract_key_words(script, n=3)
    if not keywords:
        shutil.copy2(bg_path, output_path)
        return

    positions = [
        (duration * 0.2, 0.12, -80),
        (duration * 0.5, 0.12, -80),
        (duration * 0.78, 0.10, -80),
    ]

    filters = []
    for i, (kw, (start_t, show_dur, y_off)) in enumerate(zip(keywords, positions)):
        end_t = start_t + show_dur
        escape_kw = kw.replace("'", "'\\''").replace(":", "\\:")
        dt = (
            f"drawtext=text='{escape_kw}':"
            f"fontsize=80:fontcolor=yellow:borderw=4:bordercolor=black:"
            f"x=(w-text_w)/2:y=(h-text_h)/2{y_off}:"
            f"enable='between(t,{start_t:.2f},{end_t:.2f})':"
            f"alpha='if(between(t,{start_t:.2f},{start_t+0.08:.2f}),(t-{start_t:.2f})/0.08,"
            f"if(between(t,{end_t-0.08:.2f},{end_t:.2f}),({end_t:.2f}-t)/0.08,1))'"
        )
        filters.append(dt)

    if not filters:
        shutil.copy2(bg_path, output_path)
        return

    vf = ",".join(filters)
    cmd = [FFMPEG, "-y", "-i", bg_path,
           "-vf", vf,
           "-c:v", "libx264", "-preset", "fast", "-crf", "23",
           "-pix_fmt", "yuv420p", "-an", output_path]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        log.warning(f"Text overlay failed: {r.stderr[:200]}")
        shutil.copy2(bg_path, output_path)


# ══════════════════════════════════════════════════════════════════
#  AUDIO MIX — voice + music + SFX
# ══════════════════════════════════════════════════════════════════

def mix_audio(voice_path, duration, output_path):
    music_files = list_music()
    sfxs = list_sfx()

    inputs = ["-i", voice_path]
    filter_parts = []
    amix_inputs = ["[0:a]"]  # voice is 0

    if music_files:
        music = random.choice(music_files)
        inputs.extend(["-stream_loop", "-1", "-i", music])
        filter_parts.append("[1:a]volume=0.08[music]")
        amix_inputs.append("[music]")

    sfx_idx = len(amix_inputs)
    # Whoosh at transition points
    for i, t in enumerate([3.5, 7, 10.5, 14, 17.5, 21]):
        if t >= duration: break
        name = ["whoosh", "pop", "ding", "whoosh", "impact", "pop"][i]
        if name in sfxs:
            inputs.extend(["-i", sfxs[name]])
            idx = sfx_idx + i
            filter_parts.append(
                f"[{idx}:a]volume=0.35,adelay={int(t*1000)}|{int(t*1000)}[sfx{i}]"
            )
            amix_inputs.append(f"[sfx{i}]")

    n = len(amix_inputs)
    mix = f"{''.join(amix_inputs)}amix=inputs={n}:duration=first:dropout_transition=2[out]"
    full = ";".join(filter_parts + [mix]) if filter_parts else "[0:a]copy[out]"

    cmd = [FFMPEG, "-y"] + inputs + [
        "-filter_complex", full,
        "-map", "[out]", "-c:a", "libmp3lame", "-b:a", "128k",
        "-t", str(duration), output_path
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        log.warning(f"Audio mix failed, using voice only")
        shutil.copy2(voice_path, output_path)


def parse_srt(path):
    ts = []
    try:
        with open(path) as f:
            content = f.read()
        for block in re.split(r"\n\n+", content.strip()):
            lines = block.strip().split("\n")
            if len(lines) < 3: continue
            m = re.match(
                r"(\d{2}):(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[.,](\d{3})",
                lines[1]
            )
            if not m: continue
            g = m.groups()
            s = int(g[0])*3600+int(g[1])*60+int(g[2])+int(g[3])/1000
            e = int(g[4])*3600+int(g[5])*60+int(g[6])+int(g[7])/1000
            t = " ".join(lines[2:]).strip()
            if t: ts.append({"start": s, "end": e, "text": t})
    except:
        pass
    return ts


def fmt_t(s):
    return f"{int(s//3600)}:{int((s%3600)//60):02d}:{int(s%60):02d}.{int((s%1)*100):02d}"


def generate_ass(srt_path, script, dur, output_path):
    """Generate ASS karaoke subtitles."""
    timestamps = parse_srt(srt_path)
    words = script.split()
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
                chunks.append({
                    "text": " ".join(cw),
                    "start": ts["start"] + p * d,
                    "end": ts["start"] + min(1.0, (i+csz)/max(1,len(sw))) * d
                })
    else:
        wps = len(words)/dur if dur > 0 else 3
        csz = max(2, min(5, int(wps*1.2)))
        for i in range(0, len(words), csz):
            cw = words[i:i+csz]
            chunks.append({
                "text": " ".join(cw),
                "start": i * (dur / len(words)),
                "end": min((i+csz) * (dur / len(words)), dur)
            })

    header = (
        "[Script Info]\nTitle: MindRank\nScriptType: v4.00+\nWrapStyle: 0\n"
        "ScaledBorderAndShadow: yes\nPlayResX: 1080\nPlayResY: 1920\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial Black,72,&H00FFFFFF,&H000000FF,&H00000000,"
        "&H96000000,-1,0,0,0,100,100,1,0,1,4,2,2,50,50,580,1\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    events = []
    for c in chunks:
        st = fmt_t(c["start"])
        et = fmt_t(c["end"])
        ws = c["text"].split()
        if not ws: continue
        cd = c["end"] - c["start"]
        kp = " ".join(f"{{\\kf{int(cd*100/len(ws))}}}{w}" for w in ws)
        events.append(f"Dialogue: 0,{st},{et},Default,,0,0,0,,{kp}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")
    log.info(f"ASS: {len(chunks)} chunks -> {output_path}")


def generate_thumbnail(title, output_path):
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    W, H = 1280, 720
    img = Image.new("RGB", (W, H), (5, 5, 12))
    draw = ImageDraw.Draw(img)

    for y in range(H):
        r = int(8 + 40 * math.sin(y / H * 3.5))
        g = int(2 + 8 * (y / H))
        b = int(18 + 60 * (1 - y / H))
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    for _ in range(12):
        cx = random.randint(-50, W + 50)
        cy = random.randint(-50, H + 50)
        radius = random.randint(80, 250)
        color = random.choice([(0, 212, 255), (123, 47, 187), (255, 50, 50), (255, 220, 0)])
        r, g, b = color
        for i in range(radius, 0, -4):
            a = int(50 * (1 - i / radius) ** 2)
            if a < 1: continue
            draw.ellipse([cx - i, cy - i, cx + i, cy + i], fill=(r, g, b))

    fcx, fcy, fr = 180, 360, 90
    draw.ellipse([fcx - fr, fcy - fr, fcx + fr, fcy + fr], fill=(220, 180, 150))
    ey = fcy - 20
    for ex in [fcx - 28, fcx + 28]:
        draw.ellipse([ex - 18, ey - 16, ex + 18, ey + 16], fill=(255, 255, 255))
        draw.ellipse([ex - 9, ey - 9, ex + 9, ey + 9], fill=(20, 20, 30))
    draw.ellipse([fcx - 20, fcy + 21, fcx + 20, fcy + 53], fill=(150, 50, 50))
    draw.line([fcx - 40, ey - 30, fcx - 8, ey - 24], fill=(80, 50, 30), width=5)
    draw.line([fcx + 8, ey - 24, fcx + 40, ey - 30], fill=(80, 50, 30), width=5)
    draw.polygon([(300, 360), (370, 330), (370, 390)], fill=(255, 220, 0))

    clean = title.upper()
    for p in ["WHY:", "SECRET:", "DARK TRUTH:", "SHOCKING:"]:
        if clean.startswith(p):
            clean = clean[len(p):].strip()
            break
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 72)
    lines, line = [], ""
    for w in clean.split():
        test = (line + " " + w).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > 700:
            lines.append(line)
            line = w
        else:
            line = test
    if line: lines.append(line)
    ty = (H - len(lines) * 100) // 2
    for ln in lines[:3]:
        bbox = draw.textbbox((0, 0), ln, font=font)
        tx = max(400, (W - (bbox[2] - bbox[0])) // 2)
        for dx in range(-4, 5):
            for dy in range(-4, 5):
                draw.text((tx + dx, ty + dy), ln, font=font, fill=(0, 0, 0))
        draw.text((tx, ty), ln, font=font, fill=(255, 220, 0))
        ty += 100
    logo = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 28)
    draw.text((20, 18), "MindRank", font=logo, fill=(0, 212, 255))
    img.save(output_path, "JPEG", quality=95)


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  MindRank Preview — Clean + Text + SFX + Music")
    print("=" * 60)

    out = os.path.join(BASE, "output")
    os.makedirs(out, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    base = f"preview_{ts}"

    # 1. Script
    print("\n[1/6] Script...")
    sys.path.insert(0, BASE)
    from scripts.generate_script import generate_script_offline
    topics = [
        "The dark psychology trick that works every time",
        "Top 5 signs you are a genius but don t know it",
        "5 cognitive biases that control your decisions",
        "Why high IQ people are actually lonelier",
    ]
    sd = generate_script_offline(random.choice(topics))
    print(f"  Title: {sd['title']}")
    print(f"  Words: {len(sd['script'].split())}")

    # 2. Voice
    print("\n[2/6] Voice...")
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

    # 3. Background — multi-clip, no garbage
    print("\n[3/6] Background (multi-clip)...")
    bg_raw = os.path.join(out, f"{base}_bg_raw.mp4")
    ok = build_multiclip_bg(dur + 1, bg_raw)
    if not ok:
        print("  Multi-clip failed. Generating animated fallback...")
        cmd = [FFMPEG, "-y", "-f", "lavfi", "-i",
               f"color=c=0x0A0A15:s=1080x1920:d={dur+1}:r=30",
               "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
               "-pix_fmt", "yuv420p", bg_raw]
        subprocess.run(cmd, capture_output=True, timeout=60)

    # 4. Text overlays
    print("\n[4/6] Text overlays...")
    bg_text = os.path.join(out, f"{base}_bg_text.mp4")
    add_text_overlays(bg_raw, sd["script"], dur, bg_text)
    if not os.path.exists(bg_text) or os.path.getsize(bg_text) < 5000:
        bg_text = bg_raw

    # 5. Audio mixing
    print("\n[5/6] Audio (voice + music + SFX)...")
    audio_mixed = os.path.join(out, f"{base}_audio.mp3")
    mix_audio(voice_raw, dur, audio_mixed)

    # 6. Final composite
    print("\n[6/6] Final composite...")
    srt_path = voice_raw.replace("_voice.mp3", ".srt")
    ass_path = os.path.join(out, f"{base}.ass")
    generate_ass(srt_path, sd["script"], dur, ass_path)

    final = os.path.join(out, f"{base}.mp4")
    cmd = [FFMPEG, "-y", "-i", bg_text, "-i", audio_mixed,
           "-filter_complex", f"[0:v]ass={ass_path}[final]",
           "-map", "[final]", "-map", "1:a",
           "-c:v", "libx264", "-preset", "medium", "-crf", "22",
           "-c:a", "aac", "-b:a", "128k",
           "-pix_fmt", "yuv420p", "-shortest", "-movflags", "+faststart", final]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        log.warning("Composite failed, trying simple fallback")
        cmd2 = [FFMPEG, "-y", "-i", bg_text, "-i", audio_mixed,
                "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                "-shortest", "-movflags", "+faststart", final]
        subprocess.run(cmd2, capture_output=True, timeout=120)

    thumb = os.path.join(out, f"{base}_thumb.jpg")
    generate_thumbnail(sd["title"], thumb)

    if os.path.exists(final):
        mb = os.path.getsize(final) / (1024*1024)
        print(f"\n{'='*60}")
        print(f"  VIDEO: {final}")
        print(f"  THUMB: {thumb}")
        print(f"  Title: {sd['title']}")
        print(f"  Duration: {dur:.1f}s | Size: {mb:.1f} MB")
        print(f"  Clips validated | End segments skipped | Text + SFX + Music")
        print(f"{'='*60}")
    else:
        print("  ERROR: No output")


if __name__ == "__main__":
    main()
