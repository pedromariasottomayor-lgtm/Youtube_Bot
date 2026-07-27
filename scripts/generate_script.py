"""
Step 1: Generate video script using FREE Google Gemini API or viral offline templates.
Scripts optimized for 2026 YouTube Shorts algorithm: 20-35 seconds, hook in first 2s,
pattern interrupts every 3-5s, loop trigger at end.
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

GEMINI_MODELS = [
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-1.5-flash",
]


def get_gemini_url(model):
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"


PROMPT_TEMPLATE = """You are a viral YouTube Shorts scriptwriter for "MindRank" — a psychology/facts channel.

Write a script for: "{topic}"

RULES (2026 algorithm optimized):
1. EXACTLY 80-120 words (25-35 seconds when spoken at normal pace)
2. First sentence = PATTERN INTERRUPT or CONTRADICTION (stops the scroll)
3. Every 15-20 words, add a micro-payoff (statistic, reveal, or escalation)
4. Last sentence = LOOP TRIGGER ("Watch this again and notice..." / "The last one is insane...")
5. Use short punchy sentences. No fluff. No intro. No background.
6. Specific numbers beat vague claims ("73%" better than "most")
7. Second person ("you") creates personal relevance
8. Create ONE curiosity gap and resolve it at the end

HOOK FORMULA (pick one):
- Pattern Interrupt: "Stop doing X" / "Wrong. Here's why"
- Contradiction: "Everyone thinks X. They're wrong"
- Forbidden Insider: "They don't want you to know this"
- Specific Transformation: "I did X for Y days"
- Curiosity Gap: "This one thing is the reason..."
- Identity Bait: "If you do X, you're type Y"
- Reveal Teaser: "Wait for what happens at #3"

Return ONLY valid JSON:
{{
  "title": "Title (max 50 chars, uses the hook formula)",
  "script": "Full narration (80-120 words)",
  "description": "2-3 sentences + hashtags",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "hook_formula": "Which hook formula was used"
}}

Return ONLY the JSON, no markdown, no explanation.
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


# ══════════════════════════════════════════════════════════════════
#  VIRAL OFFLINE SCRIPTS — 7 Proven Hook Formulas (2026)
#  Based on analysis of 2,400 high-retention Shorts
#  81% of 1M+ view Shorts use one of these 7 formulas
# ══════════════════════════════════════════════════════════════════

_VIRAL_SCRIPTS = [
    # ─── FORMULA 1: PATTERN INTERRUPT (38% of viral Shorts) ───
    {
        "formula": "pattern_interrupt",
        "hook": "Stop believing everything your brain tells you. It's literally lying.",
        "body": [
            "Your brain produces cortisol every morning to make you anxious. There's no tiger. Just emails.",
            "So it creates fake problems. You're not good enough. You'll fail. People are judging you. None of it is real.",
            "Scientists found your first thoughts every morning are programming from 200,000 years ago. Not truth."
        ],
        "closer": "Tomorrow morning, don't trust your first thought. Watch this again instead.",
        "title": "Your Brain Is Lying To You Every Morning",
    },
    # ─── FORMULA 2: CONTRADICTION ───
    {
        "formula": "contradiction",
        "hook": "The smartest people in the world are actually the loneliest. And there's a dark reason.",
        "body": [
            "High IQ people process information differently. They see patterns others miss. They question everything.",
            "This makes them incredible at solving problems. But terrible at connecting with people.",
            "Their brains overanalyze every interaction. Every word. Every silence. Every micro expression."
        ],
        "closer": "If you feel different from everyone around you, this is why. Watch again to feel less alone.",
        "title": "Why Smart People Are Always Lonely",
    },
    # ─── FORMULA 3: FORBIDDEN INSIDER ───
    {
        "formula": "forbidden_insider",
        "hook": "They don't want you to know this about manipulation. But here it is.",
        "body": [
            "There's a technique called anchoring. Every ad, every salary negotiation, every sale uses it.",
            "They show you a high number first so the real price feels cheap. A 500 dollar steak makes 40 dollars feel free.",
            "Your brain literally cannot evaluate anything without comparing it to the first thing it saw."
        ],
        "closer": "Now that you know this, you'll see it everywhere. You can never unsee it. Watch again.",
        "title": "Manipulation Trick Used On You 10x Daily",
    },
    # ─── FORMULA 4: SPECIFIC TRANSFORMATION ───
    {
        "formula": "specific_transformation",
        "hook": "I tracked my dopamine for 30 days. The results changed how I see everything.",
        "body": [
            "Day one, I realized I check my phone 150 times. Each check gives a micro hit of dopamine.",
            "By day fifteen, my brain couldn't sit still for two minutes. Boredom felt like pain.",
            "Day thirty, I understood. We're not addicted to phones. We're addicted to unpredictable rewards."
        ],
        "closer": "Try this. One day without your phone. Then watch this again to see what you notice.",
        "title": "I Tracked My Dopamine For 30 Days",
    },
    # ─── FORMULA 5: CURIOSITY GAP ───
    {
        "formula": "curiosity_gap",
        "hook": "There's one body language signal that reveals if someone is lying. Every single time.",
        "body": [
            "When someone tells a lie, their feet point toward the nearest exit. Always.",
            "Liars also touch their nose 4 to 8 times more than normal. It's called the nose touch response.",
            "But the biggest giveaway? Real smiles use your eyes. Fake smiles only use your mouth."
        ],
        "closer": "Watch this again and think about the last person you talked to. You'll notice everything.",
        "title": "Body Language That Exposes Every Liar",
    },
    # ─── FORMULA 6: IDENTITY BAIT ───
    {
        "formula": "identity_bait",
        "hook": "If you always feel tired but sleep eight hours, you're not lazy. You're this type.",
        "body": [
            "Empaths absorb everyone's emotions like a sponge. Their energy gets drained by people who don't even notice.",
            "Your exhaustion isn't physical. It's emotional overload. You feel everything twice. Yours and theirs.",
            "Studies show empaths have more active mirror neurons. You literally feel other people's pain."
        ],
        "closer": "You're not broken. You're rare. Watch again next time you forget why you're tired.",
        "title": "If You're Always Tired You're An Empath",
    },
    # ─── FORMULA 7: REVEAL TEASER ───
    {
        "formula": "reveal_teaser",
        "hook": "The last one on this list is the most dangerous. And most people have it.",
        "body": [
            "Number one, the perfectionist. They never start because it'll never be perfect. Paralysis by standard.",
            "Number two, the people pleaser. They say yes to everyone and burn out silently. Their kindness is a trap.",
            "Number three, the overthinker. They see every angle of every problem. Their brain never shuts off."
        ],
        "closer": "Which one are you? Be honest. Watch again to see if your type changed.",
        "title": "3 Types Of People Who Self-Sabotage",
    },
]

# Additional scripts per hook formula (variety)
_VARIETY_SCRIPTS = {
    "pattern_interrupt": [
        {
            "formula": "pattern_interrupt",
            "hook": "Delete this belief from your brain immediately. It's destroying you.",
            "body": [
                "You think you need motivation to start. That's backwards. Action creates motivation. Not the other way around.",
                "Neuroscience proves your brain releases dopamine AFTER you start. Not before. You'll never feel ready.",
                "Every successful person started before they felt prepared. They acted scared. They acted confused."
            ],
            "closer": "Start before you're ready. Watch this again when you're about to quit.",
            "title": "Delete This Belief From Your Brain",
        },
        {
            "formula": "pattern_interrupt",
            "hook": "You're not lazy. Your brain is protecting you from something terrifying.",
            "body": [
                "Procrastination isn't laziness. It's your brain avoiding discomfort. The threat isn't a bear. It's failure.",
                "Every time you procrastinate, your amygdala is screaming danger. Your brain chooses comfort over growth.",
                "This is why you procrastinate on important things but not on games. Games are safe. Growth isn't."
            ],
            "closer": "Next time you procrastinate, ask what you're really afraid of. Watch again tomorrow.",
            "title": "You're Not Lazy Your Brain Is Scared",
        },
    ],
    "contradiction": [
        {
            "formula": "contradiction",
            "hook": "The most confident people in the room are actually the most insecure.",
            "body": [
                "True confidence is quiet. It doesn't need to announce itself. The loudest person is usually the most scared.",
                "Psychologists call this overcompensation. They perform confidence to hide the void inside.",
                "Real confidence comes from accepting you don't know everything. The ego pretends. The soul accepts."
            ],
            "closer": "Confidence isn't loud. It's calm. Watch again to feel the difference.",
            "title": "The Most Confident People Are The Most Scared",
        },
        {
            "formula": "contradiction",
            "hook": "Reading books might actually be making you dumber. Here's why.",
            "body": [
                "Your brain confuses reading about something with knowing it. Knowledge feels like action but it isn't.",
                "Studies show people who read about exercise feel like they exercised. Your brain can't tell the difference.",
                "The solution isn't less reading. It's doing one thing from every book within 24 hours."
            ],
            "closer": "What's one thing you learned recently that you never applied? Watch again and do it.",
            "title": "Reading Books Is Making You Dumber",
        },
    ],
    "curiosity_gap": [
        {
            "formula": "curiosity_gap",
            "hook": "There's a 7-second trick that makes anyone trust you instantly.",
            "body": [
                "In the first 7 seconds of meeting someone, their brain decides if you're friend or threat.",
                "Eye contact for 3 seconds, a genuine smile, and mirroring their body language. That's it.",
                "Your brain releases oxytocin when it sees familiarity. Be familiar. Not perfect. Familiar."
            ],
            "closer": "Try this on the next person you meet. Watch again to master the 7 seconds.",
            "title": "7-Second Trick To Make Anyone Trust You",
        },
        {
            "formula": "curiosity_gap",
            "hook": "The color of your room is affecting your mood and you have no idea.",
            "body": [
                "Blue rooms lower your heart rate by 12 percent. Red rooms increase anxiety by 15 percent.",
                "Hospitals use green because it reduces pain perception. Offices use white because it kills creativity.",
                "Your subconscious processes color before you're even aware of it. You're being controlled by paint."
            ],
            "closer": "Look at your room right now. What color is it? Watch again to see why you feel that way.",
            "title": "Your Room Color Is Controlling Your Mood",
        },
    ],
    "forbidden_insider": [
        {
            "formula": "forbidden_insider",
            "hook": "They don't teach you this in school on purpose. It's too powerful.",
            "body": [
                "The education system was designed to create workers, not thinkers.服从, not question. Follow, not lead.",
                "Every test rewards memorization, not understanding. Every grade rewards obedience, not creativity.",
                "The most important skills are never taught. Negotiation, emotional intelligence, self-awareness."
            ],
            "closer": "The real education starts after school. Watch again to remember what they missed.",
            "title": "Why School Was Designed To Control You",
        },
    ],
    "identity_bait": [
        {
            "formula": "identity_bait",
            "hook": "If you always pick the quiet corner in every room, you're not shy. You're this.",
            "body": [
                "Introverts don't avoid people. They avoid meaningless interactions. They choose depth over width.",
                "Your brain actually processes social situations more deeply. Every conversation is a full analysis.",
                "This is why social events exhaust you. It's not weakness. It's overthinking at a superpower level."
            ],
            "closer": "You're not antisocial. You're selectively social. Watch again to own it.",
            "title": "If You Sit In The Corner You're This Type",
        },
    ],
    "reveal_teaser": [
        {
            "formula": "reveal_teaser",
            "hook": "The #1 sign someone is about to betray you. Most people miss it completely.",
            "body": [
                "Number three, they suddenly start being extra nice. Overcompensation after a decision is already made.",
                "Number two, they stop asking questions. Real friends are curious. Betrayers already know what they need.",
                "Number one, they create distance then blame you for it. They pull away so you feel guilty."
            ],
            "closer": "Think about who's been acting different lately. Watch again to see the signs.",
            "title": "The #1 Sign Someone Will Betray You",
        },
    ],
    "specific_transformation": [
        {
            "formula": "specific_transformation",
            "hook": "I stopped talking for 48 hours. What happened to my brain was terrifying.",
            "body": [
                "Hour one, my thoughts were loud. Hour six, they were screaming. I couldn't silence them.",
                "Hour twenty-four, something shifted. I started hearing thoughts I'd been drowning out for years.",
                "Hour forty-eight, I understood. Silence isn't empty. It's full of answers you've been avoiding."
            ],
            "closer": "Try one hour of silence. Just one. Then watch this again to compare your experience.",
            "title": "I Stopped Talking For 48 Hours",
        },
    ],
}


def _pick_best_script(topic: str) -> dict:
    """Pick the best script based on topic keywords, with variety."""
    topic_lower = topic.lower()

    # Keyword-to-formula mapping (which formula works best for which topic type)
    keyword_formula_map = {
        "brain": "pattern_interrupt",
        "lie": "curiosity_gap",
        "trust": "curiosity_gap",
        "manipulat": "forbidden_insider",
        "toxic": "reveal_teaser",
        "people": "identity_bait",
        "lazy": "pattern_interrupt",
        "fear": "pattern_interrupt",
        "anxiety": "pattern_interrupt",
        "smart": "contradiction",
        "confidence": "contradiction",
        "relationship": "identity_bait",
        "empath": "identity_bait",
        "phone": "pattern_interrupt",
        "body": "curiosity_gap",
        "secret": "forbidden_insider",
        "dark": "forbidden_insider",
        "habit": "specific_transformation",
        "success": "contradiction",
        "procrastinate": "pattern_interrupt",
        "decision": "curiosity_gap",
        "emotion": "identity_bait",
        "friendship": "curiosity_gap",
        "love": "identity_bait",
        "energy": "identity_bait",
        "genius": "contradiction",
        "psychology": "pattern_interrupt",
        "behavior": "curiosity_gap",
        "control": "forbidden_insider",
        "time": "specific_transformation",
    }

    # Find best matching formula for this topic
    best_formula = None
    best_score = 0
    for keyword, formula in keyword_formula_map.items():
        if keyword in topic_lower:
            score = len(keyword)
            if score > best_score:
                best_score = score
                best_formula = formula

    # Get scripts for this formula
    candidates = []
    if best_formula:
        # Add base scripts for this formula
        for s in _VIRAL_SCRIPTS:
            if s.get("formula") == best_formula:
                candidates.append(s)
        # Add variety scripts
        if best_formula in _VARIETY_SCRIPTS:
            candidates.extend(_VARIETY_SCRIPTS[best_formula])

    # Fallback: use any script with keyword match
    if not candidates:
        for s in _VIRAL_SCRIPTS:
            script_text = s.get("hook", "") + " " + " ".join(s.get("body", []))
            if any(w in script_text.lower() for w in topic_lower.split() if len(w) > 3):
                candidates.append(s)

    # Final fallback: random from all
    if not candidates:
        candidates = list(_VIRAL_SCRIPTS)
        for scripts in _VARIETY_SCRIPTS.values():
            candidates.extend(scripts)

    return random.choice(candidates)


def generate_script_offline(topic: str) -> dict:
    """Generate viral scripts offline using proven 2026 hook formulas."""
    best_match = _pick_best_script(topic)

    # Build full script
    script_text = best_match["hook"] + " " + " ".join(best_match["body"]) + " " + best_match["closer"]

    # Generate title from topic or use script title
    title = best_match.get("title") or _generate_viral_title(topic)

    # Generate tags
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
        "hook_formula": best_match.get("formula", "unknown"),
        "sections": ["Hook", "Reveal", "Deep Dive", "Mind-Blow", "Loop Trigger"],
    }


def _generate_viral_title(topic: str) -> str:
    """Generate a clickbait title — standalone, never awkward phrasing."""
    titles = [
        "This brain trick changes everything",
        "Your mind is lying to you right now",
        "97% of people don't know this",
        "This changes how you see everyone",
        "The secret nobody will tell you",
        "Your body is warning you right now",
        "Stop believing this immediately",
        "Scientists can't explain this",
        "This is why you feel empty",
        "The truth they're hiding from you",
        "Watch this before it's too late",
        "Your brain does this every morning",
        "This simple trick exposed everything",
        "Why smart people are more lonely",
        "The psychology trick that actually works",
        "You've been doing this wrong your whole life",
        "This is why you attract toxic people",
        "Your phone is rewiring your brain",
        "The friendship rule nobody teaches you",
        "This one habit is destroying you",
        "Dark psychology facts they won't teach you",
        "Why overthinking is actually a superpower",
        "The body language secret that reveals everything",
        "This is why you can't focus anymore",
        "Your worst habit is actually genetic",
    ]

    topic_lower = topic.lower()
    topic_titles = {
        "brain": ["Your brain betrays you every single day"],
        "manipulat": ["This manipulation trick works on everyone"],
        "narcissist": ["How to spot a narcissist in 10 seconds"],
        "friendship": ["The friendship rule that changes everything"],
        "body": ["Your body is screaming at you right now"],
        "love": ["This is why you keep choosing wrong"],
        "fear": ["Your fear is lying to you"],
        "success": ["The success myth that's ruining you"],
        "people": ["3 types of people you need to avoid"],
        "phone": ["Your phone is destroying your brain"],
        "dark": ["The dark truth about human nature"],
        "secret": ["A secret that changes everything"],
        "trust": ["Why trust is the biggest lie"],
        "emotion": ["Your emotions are not what you think"],
        "decision": ["Your decisions are being controlled"],
        "toxic": ["How to escape toxic people forever"],
        "habit": ["The habit loop you can't break"],
        "genius": ["Why geniuses are always misunderstood"],
        "energy": ["Protect your energy from these people"],
    }

    for keyword, alt_titles in topic_titles.items():
        if keyword in topic_lower:
            return random.choice(alt_titles)

    return random.choice(titles)


if __name__ == "__main__":
    result = generate_script_offline("The dark psychology trick that works every time")
    print(json.dumps(result, indent=2))
