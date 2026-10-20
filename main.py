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
    return {
        "index": 0,
        "videos_today": 0,
        "today": "",
        "total_uploaded": 0,
        "history": [],
        "uploaded_videos": [],
        "used_topics": [],
        "last_video_id": "",
        "last_upload": ""
    }


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

    # Skip already-used topics in history (last 500 topics)
    used = set(state.get("used_topics", [])[-500:])
    available = [t for t in TOPICS if t not in used]
    
    if not available:
        # All topics used, reset history
        state["used_topics"] = []
        available = TOPICS
        log.info("All topics used! Resetting history.")

    topic = random.choice(available)

    state["index"] = state.get("index", 0) + 1
    state["used_topics"] = state.get("used_topics", []) + [topic]
    _save_state(state)

    return topic


def get_recent_titles(limit: int = 40) -> list:
    """Return recently-used titles so the generator never repeats one."""
    state = _load_state()
    titles = []
    for entry in state.get("uploaded_videos", [])[-limit:]:
        if isinstance(entry, dict) and entry.get("title"):
            titles.append(entry["title"])
    # Also include any titles explicitly tracked
    titles.extend(state.get("used_titles", [])[-limit:])
    return list(dict.fromkeys(titles))


def get_channel_titles() -> list:
    """Fetch every title already on the channel (authoritative anti-duplicate)."""
    try:
        from scripts.upload_youtube import get_authenticated_service
        yt = get_authenticated_service()
        if not yt:
            return []
        titles, page = [], None
        while True:
            r = yt.search().list(part="snippet", forMine=True, type="video",
                                 maxResults=50, pageToken=page).execute()
            for it in r.get("items", []):
                titles.append(it["snippet"]["title"])
            page = r.get("nextPageToken")
            if not page:
                break
        return titles
    except Exception as e:
        log.warning(f"Could not fetch channel titles: {str(e)[:120]}")
        return []


def record_content(title: str, hook: str = ""):
    """Remember this title/hook so it is never reused."""
    state = _load_state()
    state["used_titles"] = (state.get("used_titles", []) + [title])[-100:]
    if hook:
        state["used_hooks"] = (state.get("used_hooks", []) + [hook])[-100:]
    _save_state(state)


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
    # Anti-duplicate: combine local state + every title already on the channel
    recent_titles = list(dict.fromkeys(get_recent_titles() + get_channel_titles()))
    log.info(f"Avoiding {len(recent_titles)} titles already used")
    script_data = generate_script(topic, avoid_titles=recent_titles)

    # If we somehow still got a duplicate title, retry with a fresh generation
    if script_data and script_data["title"] in recent_titles:
        log.warning(f"Duplicate title detected ('{script_data['title']}') — regenerating")
        for _ in range(3):
            alt = generate_script(topic, avoid_titles=recent_titles)
            if alt and alt["title"] not in recent_titles:
                script_data = alt
                break
        else:
            log.warning("Still duplicate after retries — continuing with new title suffix")

    if not script_data:
        log.error("Script generation failed. Aborting.")
        return False
    
    log.info(f"Title: {script_data['title']}")
    log.info(f"Script length: {len(script_data['script'].split())} words")
    log.info(f"Hook formula: {script_data.get('hook_formula', 'unknown')}")
    # Remember this content immediately so a retry/next run cannot repeat it
    record_content(script_data["title"], script_data.get("hook", ""))

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
        state["uploaded_videos"] = state.get("uploaded_videos", []) + [{
            "video_id": video_id,
            "title": script_data["title"],
            "topic": topic,
            "upload_time": datetime.now().isoformat(),
            "hook_formula": script_data.get("hook_formula", "unknown"),
        }]
        _save_state(state)
        cleanup_old_files()
        return True
    else:
        log.error("Upload failed.")
        return False


# ══════════════════════════════════════════════════════════════════
#  SCHEDULED SLOTS — the bot must publish in EVERY one of these
#  slots, every day. Slots are 8h / 14h / 20h UTC.
#  A slot is "filled" if a video was published in the window
#  (slot_hour - 1h, slot_hour + 5h]. This replaces the old
#  "calendar day" counter, which let a manual/test run at 00:xx
#  consume the whole day's quota and silently skip the real slots.
# ══════════════════════════════════════════════════════════════════
SLOT_HOURS_UTC = (8, 14, 20)
_SLOT_TOLERANCE_BEFORE = timedelta(hours=1)   # GitHub may fire a few min early
_SLOT_TOLERANCE_AFTER = timedelta(hours=5)    # ...or quite late after an outage


def _parse_dt(value: str):
    """Parse an ISO timestamp from state; return None if unusable."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, TypeError):
        return None


def _recent_upload_times(state: dict) -> list:
    """All upload timestamps we know about (state history + legacy fields)."""
    times = []
    for entry in state.get("uploaded_videos", []):
        if isinstance(entry, dict):
            dt = _parse_dt(entry.get("upload_time", ""))
            if dt:
                times.append(dt)
    legacy = _parse_dt(state.get("last_upload", ""))
    if legacy:
        times.append(legacy)
    return times


def is_manual_run() -> bool:
    """True when triggered by hand (workflow_dispatch) rather than the cron.

    Manual/test runs must NEVER be blocked by the daily limit — that is
    exactly how the real scheduled slots got skipped before.
    """
    return os.environ.get("GITHUB_EVENT_NAME", "") == "workflow_dispatch"


def slot_already_filled(state: dict, now: datetime) -> bool:
    """Has a video already been published in the current scheduled slot?"""
    # Determine the slot we are currently in (nearest slot within tolerance)
    slot_start = None
    for hour in SLOT_HOURS_UTC:
        candidate = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if candidate - _SLOT_TOLERANCE_BEFORE <= now <= candidate + _SLOT_TOLERANCE_AFTER:
            slot_start = candidate
            break

    if slot_start is None:
        return False  # off-slot run: always allow

    window_end = slot_start + timedelta(hours=6)
    hits = [dt for dt in _recent_upload_times(state) if slot_start <= dt < window_end]
    if hits:
        log.info(f"Slot {slot_start.strftime('%Y-%m-%d %H:%M')} UTC already has "
                 f"{len(hits)} upload(s) — nothing to do.")
        return True
    return False


if __name__ == "__main__":
    state = _load_state()
    now = datetime.utcnow()

    # Reset the legacy daily counter (kept for backwards compatibility)
    today = now.strftime("%Y-%m-%d")
    if state.get("today") != today:
        state["today"] = today
        state["videos_today"] = 0
        _save_state(state)

    manual = is_manual_run()
    log.info(f"Trigger: {'manual (workflow_dispatch)' if manual else 'scheduled'} "
             f"| now={now.strftime('%Y-%m-%d %H:%M')} UTC")

    if manual:
        # A manual run is a test/recovery: never let it eat a real slot.
        log.info("Manual run — bypassing slot limit (will not consume a scheduled slot).")
    else:
        if slot_already_filled(state, now):
            log.info("Current slot already filled. Exiting cleanly.")
            sys.exit(0)

    # Broad safety cap for the calendar day (YouTube hard limit is 6/day)
    uploads_today = [t for t in _recent_upload_times(state) if t.strftime("%Y-%m-%d") == today]
    if len(uploads_today) >= 4:
        log.info(f"Safety cap reached: {len(uploads_today)} uploads today. Skipping.")
        sys.exit(0)

    topic = get_next_topic()
    success = run_pipeline(topic)
    sys.exit(0 if success else 1)
