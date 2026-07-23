"""
YouTube Automation Bot - Main Pipeline
Runs all steps: Script → Voiceover → Video → Upload
Now with 500+ topics and auto-generation!
"""

import os
import sys
import json
import logging
import random
from datetime import datetime

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

# ─── AUTO-GENERATE NEW TOPICS ────────────────────────────────────
def generate_new_topic_with_ai():
    """Use Gemini API to generate a new unique topic."""
    try:
        from scripts.generate_script import GEMINI_API_KEY, get_gemini_url
        import urllib.request
        import urllib.error
        
        if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
            return None
            
        prompt = """Generate ONE unique YouTube Shorts topic about psychology, human behavior, or mind-blowing facts.

Rules:
- Must be catchy and make people want to click
- Must be about psychology, brain, behavior, relationships, or human nature
- Must be different from these recent topics: """ + ", ".join(random.sample(TOPICS, min(5, len(TOPICS)))) + """
- Format: Short phrase, no period at the end
- Maximum 15 words
- Return ONLY the topic text, nothing else

Examples of good topics:
- The dark secret behind every people pleaser
- Why your brain creates anxiety for no reason
- The psychological reason you fear success
- Why intelligent people are harder to brainwash
- The body language trick that reveals hidden attraction"""

        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.9,
                "maxOutputTokens": 100,
            }
        }).encode("utf-8")

        req = urllib.request.Request(
            get_gemini_url("gemini-2.0-flash-lite"),
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            topic = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            # Clean up the topic
            topic = topic.strip('"').strip("'").strip(".")
            if len(topic) > 5 and len(topic) < 100:
                log.info(f"AI generated new topic: {topic}")
                return topic
    except Exception as e:
        log.warning(f"Failed to generate topic with AI: {e}")
    return None


def get_next_topic():
    """Get the next topic - from database or AI-generated."""
    state_file = "state.json"
    if os.path.exists(state_file):
        with open(state_file) as f:
            state = json.load(f)
    else:
        state = {"index": 0, "ai_topics_used": 0}
    
    # Every 10 topics, try to generate one with AI
    if state["index"] % 10 == 0 and state["index"] > 0:
        ai_topic = generate_new_topic_with_ai()
        if ai_topic:
            state["ai_topics_used"] = state.get("ai_topics_used", 0) + 1
            with open(state_file, "w") as f:
                json.dump(state, f)
            return ai_topic
    
    # Use topic from database
    topic_index = state["index"] % len(TOPICS)
    topic = TOPICS[topic_index]
    
    # Advance to next topic
    state["index"] = state["index"] + 1
    with open(state_file, "w") as f:
        json.dump(state, f)
    
    return topic


def run_pipeline(topic: str):
    log.info(f"=== Starting pipeline for: {topic} ===")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"output/video_{timestamp}"

    # Step 1: Generate Script
    log.info("Step 1: Generating script with AI...")
    script_data = generate_script(topic)
    if not script_data:
        log.error("Script generation failed. Aborting.")
        return False
    
    log.info(f"Title: {script_data['title']}")

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
    success = generate_video(script_data, audio_path, video_path)
    if not success:
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
        log.info(f"SUCCESS! Video uploaded: https://youtube.com/watch?v={video_id}")
        return True
    else:
        log.error("Upload failed.")
        return False


if __name__ == "__main__":
    topic = get_next_topic()
    success = run_pipeline(topic)
    sys.exit(0 if success else 1)
