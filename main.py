"""
YouTube Automation Bot - Main Pipeline
Runs all steps: Script → Voiceover → Video → Upload
Posts 3x/day via GitHub Actions cron.
"""

import os
import sys
import json
import glob
import logging
import random
from datetime import datetime, timedelta

# Import all modules
from scripts.generate_script import generate_script
from scripts.generate_voice import generate_voiceover
from scripts.generate_video import generate_video
from scripts.upload_youtube import upload_to_youtube

# ─── LOGGING SETUP ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log")
    ]
)
log = logging.getLogger(__name__)

# ─── TOPICS DATABASE ─────────────────────────────────────────────
try:
    from topics_database import UNIQUE_TOPICS, get_stats
    stats = get_stats()
    log.info(f"Loaded topics database: {stats['total_topics']} topics in {stats['categories']} categories")
    TOPICS = UNIQUE_TOPICS
except ImportError:
    log.warning("Topics database not found, using default topics")
    TOPICS = [
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

STATE_FILE = "state.json"


def _load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"index": 0, "videos_today": 0, "today": "", "total_uploaded": 0, "history": []}


def _save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def get_next_topic() -> str:
    """Get the next topic from database. Never repeats within the same batch."""
    state = _load_state()

    # Reset daily counter
    today = datetime.now().strftime("%Y-%m-%d")
    if state.get("today") != today:
        state["today"] = today
        state["videos_today"] = 0

    # Skip already-used topics in history
    used = set(state.get("history", [])[-100:])  # Last 100 topics
    available = [t for t in TOPICS if t not in used]
    if not available:
        # All topics used, reset history
        state["history"] = []
        available = TOPICS

    topic = random.choice(available)

    state["index"] = state.get("index", 0) + 1
    state["history"] = state.get("history", []) + [topic]
    _save_state(state)

    return topic


def cleanup_old_files():
    """Remove old video/audio files to save disk space (keep last 3)."""
    for pattern in ["output/video_*.mp4", "output/video_*.mp3", "output/video_*.ass",
                    "output/stock_*.mp4", "output/video_*_bg.mp4"]:
        files = sorted(glob.glob(pattern))
        for f in files[:-3]:
            try:
                os.remove(f)
                log.info(f"Cleaned up: {f}")
            except OSError:
                pass


def run_pipeline(topic: str) -> bool:
    log.info(f"=== Starting pipeline for: {topic} ===")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"output/video_{timestamp}"
    os.makedirs("output", exist_ok=True)

    # Step 1: Generate Script
    log.info("Step 1: Generating script...")
    script_data = generate_script(topic)
    if not script_data:
        log.error("Script generation failed. Aborting.")
        return False
    
    log.info(f"Title: {script_data['title']}")
    log.info(f"Script length: {len(script_data['script'].split())} words")

    # Step 2: Generate Voiceover
    log.info("Step 2: Generating voiceover...")
    audio_path = f"{base_name}.mp3"
    success = generate_voiceover(script_data["script"], audio_path)
    if not success:
        log.error("Voiceover generation failed. Aborting.")
        return False

    # Step 3: Generate Video
    log.info("Step 3: Creating video...")
    video_path = f"{base_name}.mp4"
    result = generate_video(script_data, audio_path, video_path)
    if not result:
        log.error("Video generation failed. Aborting.")
        return False

    # Step 4: Upload to YouTube
    log.info("Step 4: Uploading to YouTube...")
    video_id = upload_to_youtube(
        video_path=video_path,
        title=script_data["title"],
        description=script_data["description"],
        tags=script_data["tags"],
        thumbnail_path=script_data.get("thumbnail_path")
    )

    if video_id:
        log.info(f"SUCCESS! Video uploaded: https://youtube.com/shorts/{video_id}")
        # Update state
        state = _load_state()
        state["videos_today"] = state.get("videos_today", 0) + 1
        state["total_uploaded"] = state.get("total_uploaded", 0) + 1
        state["last_video_id"] = video_id
        state["last_upload"] = datetime.now().isoformat()
        _save_state(state)
        cleanup_old_files()
        return True
    else:
        log.error("Upload failed.")
        return False


if __name__ == "__main__":
    state = _load_state()
    today = datetime.now().strftime("%Y-%m-%d")
    if state.get("today") != today:
        state["today"] = today
        state["videos_today"] = 0
        _save_state(state)

    videos_today = state.get("videos_today", 0)
    log.info(f"Videos uploaded today: {videos_today}/3")

    if videos_today >= 3:
        log.info("Daily upload limit reached. Skipping.")
        sys.exit(0)

    topic = get_next_topic()
    success = run_pipeline(topic)
    sys.exit(0 if success else 1)
