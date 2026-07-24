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
    "gemini-2.5-flash",
    "gemini-1.5-flash",
]

def get_gemini_url(model):
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"

PROMPT_TEMPLATE = """You are a YouTube Shorts creator for a channel called "MindRank" that covers psychology, human behavior, and mind-blowing facts. Create a VIRAL video package for the topic: "{topic}"

Return ONLY a valid JSON object with these exact keys:
{{
  "title": "Catchy YouTube Shorts title (max 45 chars, use power words like 'secret', 'dark', 'nobody tells you', 'shocking')",
  "script": "Full narration script (80-120 words MAXIMUM, punchy, conversational, start with a hook, end with a loop trigger)",
  "description": "YouTube Shorts description (2-3 sentences + relevant hashtags)",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "hook": "First sentence that creates instant curiosity (knowledge gap)",
  "sections": ["Hook", "Reveal", "Deep Dive", "Mind-Blow", "Loop Trigger"]
}}

VIRAL RULES (CRITICAL):
- Script MUST be 80-120 words ONLY (25-35 seconds when spoken)
- Start with the most shocking fact FIRST (in medias res)
- Every sentence must create curiosity for the next one
- End with a cliffhanger that makes them rewatch: "But here's what's crazy..." or "And the last one..."
- Use short, punchy sentences. No fluff, no setup, no background info
- The goal is to make viewers watch 2-3 times (loop effect)
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
                if "limit: 0" in error_body:
                    log.warning(f"API quota exhausted for {model} (limit: 0). Skipping...")
                    break
                wait_time = (attempt + 1) * 10
                log.warning(f"Rate limited on {model} (attempt {attempt+1}). Waiting {wait_time}s...")
                time.sleep(wait_time)
            elif e.code == 404:
                log.warning(f"Model {model} not found, trying next...")
                break
            else:
                log.warning(f"Gemini API error {e.code} on {model}: {error_body[:200]}")
                time.sleep(5)
        except json.JSONDecodeError as e:
            log.warning(f"Failed to parse response from {model}: {e}")
            return None
        except Exception as e:
            log.warning(f"Error with {model}: {e}")
            time.sleep(5)
    
    return None


def generate_script(topic: str) -> Optional[Dict]:
    """Generate video script using Gemini API with fallback to offline mode."""
    if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE" or not GEMINI_API_KEY:
        log.warning("No Gemini API key set, using offline script generation")
        return generate_script_offline(topic)

    for model in GEMINI_MODELS:
        log.info(f"Trying model: {model}")
        result = generate_script_with_model(topic, model, max_retries=1)
        if result:
            return result
        time.sleep(1)

    log.warning("All Gemini models failed, falling back to offline script generation")
    return generate_script_offline(topic)


# ─── VIRAL OFFLINE SCRIPTS ───────────────────────────────────────
# These are designed to compete with AI-generated scripts.
# Each is a complete viral package with hook, body, and loop trigger.

_VIRAL_SCRIPTS = [
    # Psychology / Dark Truths
    {
        "hook": "Your brain is literally wired to destroy your happiness and you don't even know it.",
        "body": [
            "Scientists discovered your mind has a negativity bias. It filters out good memories and amplifies bad ones. This kept your ancestors alive but it's ruining your life today.",
            "Every time something good happens, your brain ignores it within hours. But every insult? Every failure? Your brain stores those forever. You're walking around with a library of pain and a museum of joy you never visit.",
            "The worst part? You can't turn it off. Your brain is designed to notice threats, not happiness. That's why one bad comment ruins your entire day but ten compliments disappear in seconds."
        ],
        "closer": "But here's the thing your brain doesn't want you to know. Watch this again and notice how many good things you missed today.",
    },
    {
        "hook": "There's a reason toxic people are drawn to you and it's not what you think.",
        "body": [
            "Psychologists found that people with high empathy are magnetic to narcissists. Not because you're weak. Because you have something they literally cannot feel.",
            "Narcissists are emotional vampires. They can't generate their own supply of validation so they steal it from people who have too much of it. And you? You give it away without even noticing.",
            "Every time you forgive someone who hurt you, you're not being kind. You're训练 their brain that there are no consequences. You're literally training them to do it again."
        ],
        "closer": "The moment you stop explaining yourself to people who don't care, everything changes. Watch this again if you needed to hear it.",
    },
    {
        "hook": "97 percent of people will never realize their brain is lying to them every single morning.",
        "body": [
            "Your brain produces cortisol when you wake up. It's designed to make you anxious so you stay alert for danger. But there's no tiger in your kitchen. Just emails.",
            "So your brain creates fake problems. It whispers that you're not good enough. That you'll fail. That people are judging you. None of it is real but it feels absolutely real.",
            "The smartest people in history all discovered the same thing. Your first thoughts every morning are programming, not truth. Your brain is running software from 200,000 years ago in a world that no longer exists."
        ],
        "closer": "Try this tomorrow. Don't trust your first thought. Watch this again instead.",
    },
    {
        "hook": "The friendship test that psychology discovered will change how you see everyone.",
        "body": [
            "Researchers at MIT found that true friends share one specific trait. They don't just listen. They respond to your vulnerabilities with their own. That's called bidirectional self-disclosure.",
            "If you share something deep and they change the subject, that's not friendship. That's an audience. Real friends get uncomfortable together. They sit in the mess with you.",
            "The average adult loses half their friends every seven years. Not because of fights. Because of silence. The friendships that die aren't killed. They're abandoned."
        ],
        "closer": "Send this to someone you haven't talked to in a while. Watch again to remember who matters.",
    },
    {
        "hook": "Your body is sending you warning signs right now but you're completely ignoring them.",
        "body": [
            "That random twitch in your eye? Your jaw clenching? Your shoulders touching your ears? Your body is screaming at you and you keep turning up the volume.",
            "Psychologists call it somatic memory. Your body stores every stress, every trauma, every emotion you never processed. It's not in your head. It's in your muscles, your gut, your sleep.",
            "People who ignore body signals for years eventually get a wake up call they can't ignore. Chronic pain. Panic attacks. Insomnia that no pill can fix."
        ],
        "closer": "Pause right now. Where are you holding tension? That's your answer. Watch this again later when you've forgotten.",
    },
    {
        "hook": "There is a manipulation tactic so common that you fall for it 10 times a day.",
        "body": [
            "It's called anchoring. Every广告, every salary negotiation, every sale uses it against you. They show you a high number first so the real number feels like a deal.",
            "A restaurant puts a 500 dollar steak on the menu not to sell it. To make the 40 dollar dish feel reasonable. Your brain is literally incapable of evaluating anything without comparing it to the first thing it saw.",
            "This is why your ex looked better after you saw their new partner. Why a 20 percent raise feels small if your coworker got 25. Anchoring doesn't just influence your decisions. It builds your entire reality."
        ],
        "closer": "Now that you know this, you'll notice it everywhere. You can never unsee it. Watch again to catch every example.",
    },
    {
        "hook": "Scientists found the exact age your brain starts dying and it's terrifying.",
        "body": [
            "After 25 your brain begins losing 1 percent of its volume every year. Not from disease. From normal aging. By 40 you've already lost connections you'll never get back.",
            "But here's what nobody talks about. It's not memory that dies first. It's your ability to feel emotions deeply. That's why adults seem cold. They're not choosing to be. They literally can't feel as much.",
            "The good news? There's one activity that reverses this completely. Researchers at Harvard found that people who do this for 20 minutes a day have the brain of someone 10 years younger."
        ],
        "closer": "The answer is in the comments. Watch this again so you don't forget to check.",
    },
    {
        "hook": "The dark reason you keep attracting the wrong people into your life.",
        "body": [
            "Your subconscious doesn't choose who you love. It chooses who feels familiar. And if your childhood was chaotic, your brain literally interprets chaos as love.",
            "That's why healthy relationships feel boring to you. Your nervous system was calibrated for drama. Peace feels like something is wrong because you never learned what normal feels like.",
            "You're not unlucky in love. You're pattern-matching to your wounds. Every person you choose is a mirror of something you haven't healed yet."
        ],
        "closer": "This is the video you needed to see today. Watch it again tomorrow when you're ready to believe it.",
    },
    {
        "hook": "There are three types of people in this world and two of them are dangerous.",
        "body": [
            "Type one is the empath. They feel everything. They absorb other people's pain like a sponge. They give until they're empty and then wonder why they're exhausted.",
            "Type two is the narcissist. They take everything. They feed on attention and drain everyone around them. They don't love people. They love what people give them.",
            "Type three is the rarest. The awakened empath. They feel everything but they choose who gets their energy. They learned the hardest lesson. You can't save anyone who doesn't want to be saved."
        ],
        "closer": "Which type are you? Be honest. Watch again to see if your answer changes.",
    },
    {
        "hook": "Your phone is destroying your brain in ways scientists are just beginning to understand.",
        "body": [
            "Every time you check your phone, your brain releases a micro dose of dopamine. After 150 checks a day your brain starts associating boredom with reward. That's addiction.",
            "But the real damage is deeper. Studies show heavy phone users have thinner prefrontal cortices. That's the part of your brain responsible for decision making, empathy, and self control.",
            "You're not becoming antisocial. Your brain is being physically rewired to prefer screens over humans. And the scariest part? You won't notice until it's already done."
        ],
        "closer": "Put your phone down after this video. Just for five minutes. Then watch this again to see if you actually did it.",
    },
]

# Topic-specific scripts (generated for common topic patterns)
_TOPIC_SCRIPTS = {
    "manipulate": _VIRAL_SCRIPTS[1],   # toxic people
    "narcissist": _VIRAL_SCRIPTS[1],
    "brain": _VIRAL_SCRIPTS[0],         # negativity bias
    "procrastinate": _VIRAL_SCRIPTS[2], # morning cortisol
    "friendship": _VIRAL_SCRIPTS[3],    # MIT friendship test
    "body": _VIRAL_SCRIPTS[4],          # somatic memory
    "trust": _VIRAL_SCRIPTS[5],         # anchoring manipulation
    "age": _VIRAL_SCRIPTS[6],           # brain dying
    "love": _VIRAL_SCRIPTS[7],          # subconscious patterns
    "people": _VIRAL_SCRIPTS[8],        # 3 types
    "phone": _VIRAL_SCRIPTS[9],         # phone destroying brain
    "dark": _VIRAL_SCRIPTS[7],          # dark reasons
    "secret": _VIRAL_SCRIPTS[5],        # manipulation tactics
    "success": _VIRAL_SCRIPTS[2],       # brain lying
    "fear": _VIRAL_SCRIPTS[4],          # body warnings
    "anxiety": _VIRAL_SCRIPTS[2],       # morning cortisol
    "depress": _VIRAL_SCRIPTS[4],       # body signals
    "habit": _VIRAL_SCRIPTS[9],         # phone addiction
    "emotion": _VIRAL_SCRIPTS[7],       # subconscious patterns
    "relationship": _VIRAL_SCRIPTS[7],  # wrong people
    "confidence": _VIRAL_SCRIPTS[2],    # brain lying
    "energy": _VIRAL_SCRIPTS[8],        # 3 types
    "manipulat": _VIRAL_SCRIPTS[5],     # anchoring
    "control": _VIRAL_SCRIPTS[5],       # anchoring
    "toxic": _VIRAL_SCRIPTS[1],         # toxic people
    "lie": _VIRAL_SCRIPTS[2],           # brain lying
    "genius": _VIRAL_SCRIPTS[6],        # brain dying
    "smart": _VIRAL_SCRIPTS[6],
    "psychology": _VIRAL_SCRIPTS[0],
    "behavior": _VIRAL_SCRIPTS[5],
    "decision": _VIRAL_SCRIPTS[5],
}


def generate_script_offline(topic: str) -> dict:
    """
    Generate VIRAL scripts offline — designed to compete with AI output.
    Uses topic keywords to select the best matching template.
    """
    topic_lower = topic.lower()

    # Try to find a topic-specific script
    best_match = None
    best_score = 0
    for keyword, script in _TOPIC_SCRIPTS.items():
        if keyword in topic_lower:
            score = len(keyword)
            if score > best_score:
                best_score = score
                best_match = script

    # If no keyword match, pick a random script
    if not best_match:
        best_match = random.choice(_VIRAL_SCRIPTS)

    # Build the full script
    script_text = best_match["hook"] + " " + " ".join(best_match["body"]) + " " + best_match["closer"]

    # Generate a clickbait title from the topic (no prefixes like "Why:" etc)
    title = _generate_viral_title(topic)

    # Generate tags from topic
    topic_words = [w for w in topic.lower().split() if len(w) > 3][:4]
    base_tags = ["psychology", "mindrank", "facts", "humanbehavior", "mindblown", "shorts"]
    extra_tags = topic_words + ["darkpsychology", "secret", "nevertellyou"]

    return {
        "title": title,
        "script": script_text,
        "description": (
            f"Your brain is hiding something from you right now... "
            f"Follow @MindRank for more psychology facts nobody talks about. "
            f"#psychology #mindrank #facts #humanbehavior #mindblown #shorts #darkpsychology #viral"
        ),
        "tags": base_tags + extra_tags,
        "hook": best_match["hook"],
        "sections": ["Hook", "Reveal", "Deep Dive", "Mind-Blow", "Loop Trigger"],
    }


def _generate_viral_title(topic: str) -> str:
    """Generate a clickbait title from topic — no prefixes, maximum impact."""
    templates = [
        "This {topic} fact will change how you see everything",
        "Nobody tells you this about {topic}",
        "Your brain is lying about {topic}",
        "The dark truth about {topic} they hiding from you",
        "I can't believe {topic} is actually this messed up",
        "Stop believing this about {topic}",
        "Scientists can't explain why {topic} works like this",
        "You've been wrong about {topic} your whole life",
        "{topic}? The answer will shock you",
        "This {topic} secret is buried for a reason",
    ]

    topic_clean = topic.lower().strip()
    # Remove common prefixes
    for prefix in ["the ", "why ", "how ", "what ", "top 5 ", "top 10 ", "5 ", "10 "]:
        if topic_clean.startswith(prefix):
            topic_clean = topic_clean[len(prefix):]
            break

    title = random.choice(templates).format(topic=topic_clean.title())

    # Ensure max 60 chars
    if len(title) > 60:
        title = title[:57] + "..."

    return title


if __name__ == "__main__":
    result = generate_script_offline("The dark psychology trick that works every time")
    print(json.dumps(result, indent=2))
