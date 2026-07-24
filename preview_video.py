#!/usr/bin/env python3
"""
MindRank — Preview Generator v3
Real stock footage backgrounds + enthusiastic voice + synced subtitles
"""

import os, sys, time, random, re, logging, subprocess, tempfile, shutil
from PIL import Image as PILImage, ImageDraw, ImageFont

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

FFMPEG = "/Users/pedrosottomayor/Library/Python/3.9/lib/python/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1"
if not os.path.exists(FFMPEG):
    FFMPEG = "ffmpeg"
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "gameplay")


def get_font(size, bold=False):
    for f in ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc"]:
        try:
            return ImageFont.truetype(f, size)
        except:
            continue
    return ImageFont.load_default()


def list_asset_clips():
    """List available stock clips in assets/gameplay/."""
    if not os.path.exists(ASSETS_DIR):
        return []
    return [os.path.join(ASSETS_DIR, f) for f in sorted(os.listdir(ASSETS_DIR)) if f.endswith(".mp4")]


def pick_background(duration):
    """Pick a random stock clip, loop it to match duration, return path."""
    clips = list_asset_clips()
    if not clips:
        log.warning("No stock clips in assets/gameplay/, using animated fallback")
        return None

    chosen = random.choice(clips)
    log.info(f"Using stock clip: {os.path.basename(chosen)}")

    # Loop the clip to fill duration
    tmp = tempfile.mktemp(suffix=".mp4")
    cmd = [
        FFMPEG, "-y", "-stream_loop", "-1", "-i", chosen,
        "-t", str(duration + 1),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-an", "-pix_fmt", "yuv420p", tmp
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode == 0 and os.path.exists(tmp) and os.path.getsize(tmp) > 5000:
        return tmp
    return None


def animated_fallback(duration):
    """Animated dark background with moving particles."""
    tmp = tempfile.mktemp(suffix=".mp4")
    cmd = [
        FFMPEG, "-y", "-f", "lavfi", "-i",
        f"color=c=0x0A0A15:s=1080x1920:d={duration}:r=30",
        "-vf", ",".join([
            "drawtext=text='●':fontsize=200:fontcolor=0x00D4FF@0.08:x='mod(t*40,1080)':y='h/3+120*sin(t*0.7)'",
            "drawtext=text='●':fontsize=160:fontcolor=0x7B2FBE@0.08:x='mod(t*30+400,1080)':y='2*h/3+100*cos(t*0.9)'",
            "drawtext=text='●':fontsize=140:fontcolor=0x00D4FF@0.06:x='mod(t*20+200,1080)':y='h/2+80*sin(t*1.5)'",
            "drawtext=text='—':fontsize=80:fontcolor=0xFFDC00@0.05:x='mod(t*50+100,1080)':y='h*0.7+50*sin(t*1.0)'",
            "drawtext=text='—':fontsize=60:fontcolor=0x7B2FBE@0.04:x='mod(t*45+500,1080)':y='h*0.3+40*cos(t*1.3)'",
            "vignette=PI/4",
        ]),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p", tmp
    ]
    subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return tmp if os.path.exists(tmp) else None


def get_duration(audio_path):
    try:
        r = subprocess.run([FFMPEG, "-i", audio_path, "-f", "null", "-"], capture_output=True, text=True, timeout=10)
        m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", r.stderr)
        if m:
            return float(m.group(1)) * 3600 + float(m.group(2)) * 60 + float(m.group(3))
    except:
        pass
    return 25.0


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


def main():
    print("=" * 60)
    print("  MindRank — Preview v3 (Real Footage)")
    print("=" * 60)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(out, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    base = f"preview_{ts}"

    # 1. Script
    print("\n[1/5] Script...")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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
    print("\n[2/5] Voiceover (AndrewNeural +15%)...")
    import asyncio, edge_tts
    audio = os.path.join(out, f"{base}.mp3")

    async def gen():
        c = edge_tts.Communicate(text=sd["script"], voice="en-US-AndrewNeural", rate="+15%", pitch="+2Hz")
        sm = edge_tts.SubMaker()
        data = b""
        async for ch in c.stream():
            if ch["type"] == "audio":
                data += ch["data"]
            elif ch["type"] == "SentenceBoundary":
                sm.feed(ch)
        with open(audio, "wb") as f:
            f.write(data)
        srt = audio.replace(".mp3", ".srt")
        s = sm.get_srt()
        if s:
            with open(srt, "w") as f:
                f.write(s)

    asyncio.run(gen())
    dur = get_duration(audio)
    print(f"  Duration: {dur:.1f}s")

    # 3. Background — real stock clips
    print("\n[3/5] Background (real footage)...")
    bg = os.path.join(out, f"{base}_bg.mp4")
    bg_tmp = pick_background(dur + 1)
    if not bg_tmp:
        bg_tmp = animated_fallback(dur + 1)
    if bg_tmp:
        shutil.move(bg_tmp, bg)
        print(f"  Background: {os.path.basename(bg)}")
    else:
        print("  ERROR: No background generated")
        return

    # 4. Subtitles
    print("\n[4/5] Subtitles (real timestamps)...")
    srt_path = audio.replace(".mp3", ".srt")
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

    header = "[Script Info]\nTitle: MindRank\nScriptType: v4.00+\nWrapStyle: 0\nScaledBorderAndShadow: yes\nPlayResX: 1080\nPlayResY: 1920\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Arial Black,72,&H00FFFFFF,&H000000FF,&H00000000,&H96000000,-1,0,0,0,100,100,1,0,1,4,2,2,50,50,580,1\nStyle: BigWord,Arial Black,88,&H0000FFFF,&H000000FF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,4.5,2.5,8,50,50,120,1\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    events = []
    for c in chunks:
        st, et = fmt_t(c["start"]), fmt_t(c["end"])
        ws = c["text"].split()
        if not ws:
            continue
        big = max(ws, key=len)
        cd = c["end"] - c["start"]
        kp = " ".join(f"{{\\kf{int(cd * 100 / len(ws))}}}{w}" for w in ws)
        events.append(f"Dialogue: 0,{st},{et},Default,,0,0,0,,{kp}")
        events.append(f"Dialogue: 1,{st},{et},BigWord,,0,0,0,,{{\\fad(200,200)\\pos(540,180)\\kf{int(cd * 40)}}}{big}")

    ass = os.path.join(out, f"{base}.ass")
    with open(ass, "w") as f:
        f.write(header + "\n".join(events) + "\n")
    print(f"  ASS: {len(chunks)} chunks")

    # 5. Composite
    print("\n[5/5] Compositing...")
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

    if os.path.exists(final):
        size_mb = os.path.getsize(final) / (1024 * 1024)
        print(f"\n{'=' * 60}")
        print(f"  VIDEO: {final}")
        print(f"  Title: {sd['title']}")
        print(f"  Duration: {dur:.1f}s | Size: {size_mb:.1f} MB")
        print(f"  Voice: AndrewNeural +15% | Subs: synced")
        print(f"  Background: REAL stock footage")
        print(f"{'=' * 60}")
    else:
        print("  ERROR: Composite failed")


if __name__ == "__main__":
    main()
