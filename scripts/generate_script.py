"""
Step 1: Generate video script using FREE Google Gemini API
Get your free API key at: https://aistudio.google.com/app/apikey
Now with retry logic, multiple models, and offline fallback!
"""

import os
import json
import time
import urllib.request
import urllib.error
import logging
import random
from typing import Optional, Dict

log = logging.getLogger(__name__)

# ─── CONFIG ──────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Multiple models to try (in order of preference)
GEMINI_MODELS = [
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
]

def get_gemini_url(model):
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"

PROMPT_TEMPLATE = """You are a YouTube content creator for a channel called "MindRank" that covers psychology, human behavior, and mind-blowing facts. Create a complete video package for the topic: "{topic}"

Return ONLY a valid JSON object with these exact keys:
{{
  "title": "Catchy YouTube title (max 60 chars, use power words like 'secret', 'dark', 'nobody tells you')",
  "script": "Full video narration script (150-200 words, engaging, conversational, start with a hook, no timestamps)",
  "description": "YouTube video description (2-3 sentences + relevant hashtags)",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "hook": "First sentence to grab attention immediately",
  "sections": ["Section 1 title", "Section 2 title", "Section 3 title"]
}}

Rules:
- Script must flow naturally when spoken aloud
- Start with the hook to grab attention immediately
- End with a call to action (like and subscribe for more)
- Tags should be relevant single words or short phrases
- Use short sentences for better voiceover pacing
- Return ONLY the JSON, no markdown, no extra text, no explanation
"""


def generate_script_with_model(topic: str, model: str, max_retries: int = 2) -> Optional[Dict]:
    """Try to generate script with a specific model, with retries."""
    url = get_gemini_url(model)
    prompt = PROMPT_TEMPLATE.format(topic=topic)
    
    for attempt in range(max_retries):
        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1024,
            }
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()

                # Remove markdown code fences if present
                if text.startswith("```"):
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                if text.endswith("```"):
                    text = text.rsplit("```", 1)[0]

                result = json.loads(text.strip())
                log.info(f"Script generated with {model}: {result.get('title', 'No title')}")
                return result

        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            if e.code == 429:
                # Check if quota is completely exhausted (limit: 0)
                if "limit: 0" in error_body:
                    log.warning(f"API quota exhausted for {model} (limit: 0). Skipping...")
                    break  # Don't retry, try next model
                wait_time = (attempt + 1) * 10  # 10s, 20s
                log.warning(f"Rate limited on {model} (attempt {attempt+1}). Waiting {wait_time}s...")
                time.sleep(wait_time)
            elif e.code == 404:
                log.warning(f"Model {model} not found, trying next...")
                break  # Don't retry 404s, try next model
            else:
                log.warning(f"Gemini API error {e.code} on {model}: {error_body[:200]}")
                time.sleep(5)
        except json.JSONDecodeError as e:
            log.warning(f"Failed to parse response from {model}: {e}")
            return None  # Don't retry JSON parse errors
        except Exception as e:
            log.warning(f"Error with {model}: {e}")
            time.sleep(5)
    
    return None


def generate_script(topic: str) -> Optional[Dict]:
    """Generate video script using Gemini API with fallback to offline mode."""
    if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE" or not GEMINI_API_KEY:
        log.warning("No Gemini API key set, using offline script generation")
        return generate_script_offline(topic)

    # Try each model in order (with short timeouts)
    for model in GEMINI_MODELS:
        log.info(f"Trying model: {model}")
        result = generate_script_with_model(topic, model, max_retries=1)
        if result:
            return result
        time.sleep(1)  # Brief pause between model attempts

    # All models failed - fall back to offline
    log.warning("All Gemini models failed, falling back to offline script generation")
    return generate_script_offline(topic)


# ─── OFFLINE FALLBACK ────────────────────────────────────────────
def generate_script_offline(topic: str) -> dict:
    """Generate a better offline script with topic-specific content."""
    
    # Topic-specific script templates
    templates = {
        "psychology": [
            f"Did you know that {topic.lower()} is one of the most fascinating discoveries in psychology? "
            "Scientists have spent decades studying this phenomenon, and what they found will change how you see the world. "
            "Your brain does things you never noticed, and this is one of them. "
            "The way we think, feel, and behave is controlled by hidden patterns that most people never discover. "
            "Understanding these patterns gives you power over your own mind. "
            "Most people go through life without ever realizing how their brain truly works. "
            "But today, we're pulling back the curtain on one of psychology's most shocking secrets. "
            "Stay until the end because the final revelation will blow your mind. "
            "If you found this fascinating, smash that like button and subscribe to MindRank "
            "for more incredible psychological insights every single day!",
        ],
        "default": [
            f"Here's something absolutely incredible about {topic.lower()} that most people never realize. "
            "The truth is far more surprising than you could ever imagine. "
            "Scientists have been studying this for years, and the results are mind-blowing. "
            "What you're about to learn will completely change your perspective on the world. "
            "Most people walk around every day without knowing this fascinating truth. "
            "But once you understand it, you'll start seeing it everywhere. "
            "The human brain is an amazing machine, and what it does with this information is extraordinary. "
            "Watch until the end because the last fact is the most shocking of all. "
            "If you enjoyed this, hit subscribe to MindRank for daily mind-blowing facts!",
        ],
    }
    
    # Pick template based on keywords
    template_key = "default"
    psych_keywords = ["psychology", "brain", "mind", "behavior", "emotion", "fear", "anxiety", 
                      "relationship", "personality", "manipulation", "body language", "cognitive"]
    for kw in psych_keywords:
        if kw in topic.lower():
            template_key = "psychology"
            break
    
    script_text = " ".join(templates[template_key])
    
    # Generate SEO-friendly title
    power_words = ["Secret", "Dark Truth", "Nobody Tells You", "Shocking", "Mind-Blowing", 
                   "Hidden", "Exposed", "Psychology", "Why", "How"]
    title_word = random.choice(power_words)
    title = f"{title_word}: {topic}"
    if len(title) > 60:
        title = topic[:57] + "..."
    
    return {
        "title": title,
        "script": script_text,
        "description": (
            f"Discover the truth about {topic.lower()} in this mind-blowing video! "
            f"We explore the hidden psychology behind human behavior that nobody talks about. "
            f"#psychology #mindrank #facts #humanbehavior #mindblown #shorts"
        ),
        "tags": ["psychology", "facts", "mindblown", "humanbehavior", "mindrank", 
                 topic.lower().split()[0], topic.lower().split()[-1]],
        "hook": f"Here's something incredible about {topic.lower()} that most people never realize",
        "sections": ["The Hidden Truth", "Why It Matters", "The Mind-Blowing Conclusion"]
    }


if __name__ == "__main__":
    result = generate_script_offline("The dark psychology trick that works every time")
    print(json.dumps(result, indent=2))
