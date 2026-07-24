"""
Pexels Stock Footage Downloader
Downloads free vertical stock videos for YouTube Shorts background.
API: https://www.pexels.com/api/ (free, 200 req/hour)
"""

import os
import json
import random
import logging
import subprocess

try:
    import requests
except ImportError:
    requests = None

from typing import List, Dict, Optional

log = logging.getLogger(__name__)

PEXELS_API_URL = "https://api.pexels.com"


def _get_api_key() -> str:
    """Get Pexels API key from environment."""
    if requests is None:
        log.warning("requests library not installed. Cannot download stock footage.")
        return ""
    key = os.environ.get("PEXELS_API_KEY", "")
    if not key:
        log.warning("PEXELS_API_KEY not set. Cannot download stock footage.")
    return key


def search_videos(query: str, per_page: int = 10, orientation: str = "portrait") -> List[Dict]:
    """Search Pexels for videos matching a query."""
    api_key = _get_api_key()
    if not api_key:
        return []

    headers = {"Authorization": api_key}
    params = {
        "query": query,
        "per_page": per_page,
        "orientation": orientation,
        "size": "medium",
    }

    try:
        resp = requests.get(f"{PEXELS_API_URL}/videos/search",
                          headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        videos = data.get("videos", [])
        log.info(f"Pexels: Found {len(videos)} videos for '{query}'")
        return videos
    except Exception as e:
        log.warning(f"Pexels search failed: {e}")
        return []


def _pick_best_video(videos: List[Dict], min_duration: float = 3.0) -> Optional[Dict]:
    """Pick the best video file from search results (prefer HD, longer clips)."""
    if not videos:
        return None

    candidates = []
    for video in videos:
        duration = video.get("duration", 0)
        if duration < min_duration:
            continue
        # Get video files
        files = video.get("video_files", [])
        for f in files:
            width = f.get("width", 0)
            height = f.get("height", 0)
            # Prefer portrait orientation (height > width)
            if height > width and width >= 720:
                candidates.append({
                    "url": f.get("link", ""),
                    "width": width,
                    "height": height,
                    "duration": duration,
                    "quality": f.get("quality") or "",
                    "video_id": video.get("id", 0),
                })

    if not candidates:
        # Fallback: any video with decent resolution
        for video in videos:
            files = video.get("video_files", [])
            for f in files:
                if f.get("width", 0) >= 720:
                    candidates.append({
                        "url": f.get("link", ""),
                        "width": f.get("width", 0),
                        "height": f.get("height", 0),
                        "duration": video.get("duration", 0),
                        "quality": f.get("quality") or "",
                        "video_id": video.get("id", 0),
                    })

    if not candidates:
        return None

    # Prefer HD quality
    hd = [c for c in candidates if "hd" in str(c.get("quality") or "").lower() or c["height"] >= 1080]
    if hd:
        return random.choice(hd)
    return random.choice(candidates)


def download_video(url: str, output_path: str, timeout: int = 60) -> bool:
    """Download a video file from URL."""
    if requests is None:
        return False
    try:
        resp = requests.get(url, stream=True, timeout=timeout)
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        log.info(f"Downloaded: {output_path} ({size_mb:.1f} MB)")
        return True
    except Exception as e:
        log.warning(f"Download failed: {e}")
        return False


def crop_to_vertical(input_path: str, output_path: str, width: int = 1080, height: int = 1920) -> bool:
    """Crop and scale a video to 9:16 vertical format using FFmpeg."""
    # Center crop + scale to target dimensions
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", (
            f"crop=ih*9/16:ih:(iw-ih*9/16)/2:0,"
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black"
        ),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-an",  # Remove original audio
        "-pix_fmt", "yuv420p",
        output_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.returncode == 0
    except Exception as e:
        log.warning(f"Crop failed: {e}")
        return False


def get_stock_for_script(script: str, work_dir: str, audio_duration: float) -> List[str]:
    """
    Analyze script and download relevant stock footage clips.
    Returns list of paths to cropped vertical video clips.
    """
    api_key = _get_api_key()
    if not api_key:
        log.warning("No Pexels API key - skipping stock footage")
        return []

    # Extract keywords from script for searching
    keywords = _extract_keywords(script)
    log.info(f"Stock footage keywords: {keywords}")

    clips = []
    clips_needed = max(3, int(audio_duration / 5))  # ~1 clip per 5 seconds

    for keyword in keywords[:clips_needed * 2]:  # Search more than needed
        if len(clips) >= clips_needed:
            break

        videos = search_videos(keyword, per_page=5)
        video = _pick_best_video(videos)

        if not video or not video.get("url"):
            continue

        # Download
        raw_path = os.path.join(work_dir, f"stock_raw_{len(clips)}.mp4")
        if not download_video(video["url"], raw_path):
            continue

        # Crop to vertical
        cropped_path = os.path.join(work_dir, f"stock_{len(clips)}.mp4")
        if crop_to_vertical(raw_path, cropped_path):
            clips.append(cropped_path)
            log.info(f"Stock clip {len(clips)}: {keyword} -> {cropped_path}")
            # Remove raw file
            try:
                os.remove(raw_path)
            except OSError:
                pass
        else:
            # Use raw file if crop fails
            clips.append(raw_path)

    log.info(f"Downloaded {len(clips)} stock clips")
    return clips


def download_pixabay_clips(work_dir: str, audio_duration: float, count: int = 4) -> List[str]:
    """Download free gameplay/satisfying clips from Pixabay (no API key needed)."""
    import requests as req

    queries = [
        "satisfying loop abstract neon",
        "parkour running urban",
        "colorful candy falling",
        "neon tunnel light speed",
        "marble run satisfying",
        "subway train station moving",
        "city night time lapse driving",
        "fire flames mesmerizing close up",
        "underwater bubbles colorful",
        "smoke colored powder explosion",
        "ink water abstract beautiful",
        "aurora borealis timelapse",
    ]
    random.shuffle(queries)

    clips = []
    for i, query in enumerate(queries[:count * 2]):
        if len(clips) >= count:
            break
        try:
            resp = req.get(
                "https://pixabay.com/api/videos/",
                params={"q": query.replace(" ", "+"), "per_page": 3, "min_width": 720},
                timeout=15
            )
            if resp.status_code != 200:
                continue
            hits = resp.json().get("hits", [])
            if not hits:
                continue
            video = random.choice(hits)
            vids = video.get("videos", {})
            vid = vids.get("medium") or vids.get("large") or vids.get("small")
            if not vid or not vid.get("url"):
                continue
            raw_path = os.path.join(work_dir, f"pixabay_raw_{len(clips)}.mp4")
            r = req.get(vid["url"], stream=True, timeout=60)
            r.raise_for_status()
            with open(raw_path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            # Crop to vertical
            cropped = os.path.join(work_dir, f"pixabay_{len(clips)}.mp4")
            cmd = [
                "ffmpeg", "-y", "-i", raw_path,
                "-vf", "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-an", "-pix_fmt", "yuv420p", cropped
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0 and os.path.exists(cropped):
                clips.append(cropped)
                log.info(f"Pixabay clip {len(clips)}: {query}")
                try:
                    os.remove(raw_path)
                except OSError:
                    pass
            else:
                clips.append(raw_path)
        except Exception as e:
            log.debug(f"Pixabay failed for '{query}': {e}")
            continue

    log.info(f"Downloaded {len(clips)} Pixabay clips")
    return clips


def _extract_keywords(script: str) -> List[str]:
    """Extract visual keywords from script for stock footage search."""
    # Map script topics to visual search terms
    keyword_map = {
        # Psychology/mind
        "brain": "brain thinking mind",
        "mind": "person thinking psychology",
        "think": "person thinking deep thought",
        "thought": "person thinking ideas",
        "psychology": "psychology brain mind",
        "manipulate": "person manipulation control",
        "manipulation": "person manipulation control",
        "trick": "magic trick surprise",
        "secret": "mystery secret hidden",
        # People/emotions
        "people": "crowd people walking city",
        "person": "person walking alone",
        "happy": "person happy celebration joy",
        "sad": "person sad lonely",
        "angry": "person angry frustration",
        "fear": "person scared afraid dark",
        "love": "couple love romantic",
        "trust": "handshake trust business",
        "lie": "person lying deception",
        "truth": "truth revelation light",
        # Actions
        "work": "person working office desk",
        "success": "success achievement celebration",
        "fail": "failure falling down",
        "money": "money cash business",
        "time": "clock time passing",
        "learn": "person studying learning",
        "discover": "discovery exploration adventure",
        "change": "transformation change before after",
        "power": "power strength leadership success",
        "control": "control power leadership business",
        "nature": "nature beautiful landscape aerial",
        "city": "city night skyline lights",
        "space": "space galaxy stars nebula",
        "water": "ocean waves water beautiful",
        "fire": "fire flames burning mesmerizing",
        "rain": "rain falling water drops window",
        "night": "night city neon lights urban",
        "dark": "dark night shadow mystery cinematic",
        "light": "light sunrise hope beautiful",
        "danger": "danger warning risk dramatic",
        "risk": "risk danger adventure extreme",
        "goal": "goal target achievement success",
        "dream": "dream sky clouds imagination beautiful",
        "future": "future technology city neon",
        "history": "history ancient old ruins",
        "science": "science laboratory experiment",
        "money": "money cash business success",
        "time": "clock time passing city",
        "brain": "brain thinking mind psychology",
        "secret": "mystery secret hidden dark",
        "truth": "truth revelation light dramatic",
        "lie": "person lying deception dark",
        "trust": "handshake trust business people",
        "love": "couple love romantic beautiful",
        "fear": "person scared afraid dark shadow",
        "anger": "person angry frustration dramatic",
        "happy": "person happy celebration joy beautiful",
        "sad": "person sad lonely rain",
        "success": "success achievement celebration beautiful",
        "fail": "failure falling dramatic dark",
        "discover": "discovery exploration adventure beautiful",
        "change": "transformation change beautiful",
        "learn": "person studying learning beautiful",
        "work": "person working office desk modern",
        "people": "crowd people walking city",
        "person": "person walking alone cinematic",
    }

    words = script.lower().split()
    found_keywords = []

    for word in words:
        word_clean = word.strip(".,!?;:'\"")
        if word_clean in keyword_map:
            found_keywords.append(keyword_map[word_clean])

    # Always add some engaging visual keywords (satisfying/mesmerizing footage)
    # These are the "visual hook" clips that keep people watching
    generic = [
        "satisfying loop abstract neon",
        "city night time lapse driving",
        "ocean waves aerial beautiful blue",
        "neon lights city cyberpunk street",
        "nature timelapse clouds stunning",
        "space stars galaxy cinematic",
        "rain on window cozy moody",
        "fire flames mesmerizing close up slow",
        "underwater bubbles colorful light",
        "kinetic sand cutting satisfying",
        "smoke colored powder explosion slow",
        "light painting abstract colorful",
        "water drops macro beautiful",
        "aurora borealis northern lights timelapse",
        "hot air balloon festival colorful sky",
        "coffee pour slow motion aesthetic",
        "ink in water beautiful abstract",
        "string lights bokeh night aesthetic",
        "cherry blossom petals falling beautiful",
        "wave crash ocean cinematic slow",
    ]

    # Merge found + generic, remove duplicates
    all_keywords = found_keywords + generic
    random.shuffle(all_keywords)

    # Return unique keywords
    seen = set()
    result = []
    for kw in all_keywords:
        if kw not in seen:
            seen.add(kw)
            result.append(kw)

    return result[:8]


# ══════════════════════════════════════════════════════════════════
#  VIDEO CONCATENATION
# ══════════════════════════════════════════════════════════════════

def concatenate_clips(clips: List[str], output_path: str, target_duration: float) -> bool:
    """Concatenate multiple clips into one video, looping if needed to match duration."""
    if not clips:
        return False

    if len(clips) == 1:
        # Just trim/pad single clip to target duration
        cmd = [
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", clips[0],
            "-t", str(target_duration),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            output_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            return result.returncode == 0
        except Exception:
            return False

    # Create concat file
    concat_file = output_path + ".concat.txt"
    with open(concat_file, "w") as f:
        # Loop clips to fill duration
        total = 0
        idx = 0
        while total < target_duration + 2:
            clip = clips[idx % len(clips)]
            f.write(f"file '{os.path.abspath(clip)}'\n")
            # Get clip duration
            try:
                probe = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "default=noprint_wrappers=1:nokey=1", clip],
                    capture_output=True, text=True, timeout=10
                )
                dur = float(probe.stdout.strip())
            except Exception:
                dur = 5.0
            total += dur
            idx += 1

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-t", str(target_duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        output_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        os.remove(concat_file)
        return result.returncode == 0
    except Exception as e:
        log.warning(f"Concat failed: {e}")
        return False
