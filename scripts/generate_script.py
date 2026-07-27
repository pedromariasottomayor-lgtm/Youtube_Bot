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
#  TEMPLATE-BASED SCRIPT GENERATOR — 100% unique per topic
#  Uses topic keywords to generate custom hooks, body, and closers
# ══════════════════════════════════════════════════════════════════

# Hook templates — each generates a unique opening based on topic
_HOOK_TEMPLATES = [
    # Pattern Interrupt
    "Stop believing everything {topic_word} tells you. It's literally lying.",
    "Wrong. {topic_word} isn't what you think. Here's why.",
    "Delete this belief about {topic_word} immediately. It's destroying you.",
    "Your brain is wrong about {topic_word}. And it's costing you everything.",
    # Contradiction
    "Everyone thinks {topic_word} is {positive}. They're completely wrong.",
    "The truth about {topic_word} will make you uncomfortable. But you need to hear it.",
    "Most people get {topic_word} completely backwards. Here's what actually happens.",
    "{topic_word} isn't {positive}. It's the opposite. And here's proof.",
    # Forbidden Insider
    "They don't want you to know this about {topic_word}. But here it is.",
    "This {topic_word} secret has been hidden for years. Until now.",
    "Psychologists discovered something terrifying about {topic_word}. They buried it.",
    "The dark truth about {topic_word} that nobody will tell you.",
    # Curiosity Gap
    "There's one {topic_word} signal that reveals everything. Every single time.",
    "This one thing about {topic_word} changes how you see everything.",
    "Scientists found something shocking about {topic_word}. You won't believe it.",
    "The {topic_word} secret that 97% of people don't know.",
    # Identity Bait
    "If you {action}, you're not {negative}. You're this type.",
    "People who {action} have something different in their brain. It's not what you think.",
    "If {condition}, your brain is wired differently. Here's why.",
    "You're not {negative}. Your {topic_word} is a superpower. Here's proof.",
    # Reveal Teaser
    "The last {topic_word} fact on this list is the most insane. Most people have it.",
    "Number three will change how you see {topic_word} forever.",
    "Wait until you hear #2. It explains everything about {topic_word}.",
    "The {topic_word} sign nobody talks about. But everyone should.",
    # Specific Transformation
    "I tracked my {topic_word} for 30 days. What happened changed everything.",
    "I stopped ignoring my {topic_word} for 48 hours. The results were terrifying.",
    "I tested this {topic_word} trick for 7 days. The difference was insane.",
    "I analyzed 1000 people's {topic_word}. The pattern was terrifying.",
]

# Body templates — 3 paragraphs that expand on the hook
_BODY_TEMPLATES = [
    [
        "Your brain processes {topic_word} in two different systems. The first is fast and automatic. The second is slow and deliberate.",
        "Most people only use the fast system. It's efficient but flawed. It makes assumptions. It sees patterns that don't exist.",
        "The slow system is where truth lives. But it takes effort. And your brain hates effort. So it shortcuts. Every time."
    ],
    [
        "Scientists studied {topic_word} for 20 years. The findings were disturbing. Your brain doesn't want you to know this.",
        "When {topic_word} happens, your amygdala fires before your logic can catch up. You're reacting from fear, not truth.",
        "The solution isn't harder thinking. It's awareness. Notice when your brain is reacting from fear. That's when it lies most."
    ],
    [
        "Here's what most people miss about {topic_word}: it's not about willpower. It's about environment.",
        "Your surroundings control 80% of your {topic_word} behavior. You're not choosing. You're responding to triggers.",
        "Change the environment first. The behavior follows. Not the other way around. This is why most people fail at {topic_word}."
    ],
    [
        "The first 7 seconds of {topic_word} determine everything. After that, your brain has already decided.",
        "This is called thin-slicing. Your subconscious processes {topic_word} faster than your conscious mind can think.",
        "The problem? Your subconscious is biased. It uses old data. Old fears. Old patterns. Not current reality."
    ],
    [
        "There's a reason {topic_word} feels impossible to change. Your neurons have been firing the same way for years.",
        "Every time you {topic_word}, you strengthen that neural pathway. It becomes automatic. Like driving home without thinking.",
        "But here's the secret: new pathways can form at any age. Your brain is more plastic than you think. The key is repetition."
    ],
    [
        "Your brain releases dopamine BEFORE {topic_word}. Not after. That's why you keep doing it even when it hurts.",
        "This is called anticipatory dopamine. It's more powerful than the reward itself. Your brain is addicted to wanting, not having.",
        "Understanding this changes everything. You're not weak. Your neurochemistry is working against you. Know the game. Beat the game."
    ],
    [
        "Studies show {topic_word} activates the same brain regions as physical pain. It's not in your head. It's in your neurons.",
        "This is why {topic_word} feels so terrible. Your brain literally processes it as danger. The threat response is real.",
        "The fix isn't to ignore it. It's to reframe it. Your brain can't distinguish between a bear and a deadline. Both are threats. Neither will kill you."
    ],
    [
        "Here's the counterintuitive truth about {topic_word}: trying harder makes it worse.",
        "When you force {topic_word}, your prefrontal cortex overloads. You make worse decisions. You see fewer options.",
        "The solution? Step back. Let your default mode network work. Your brain solves problems best when you're not trying."
    ],
]

# Closer templates — loop trigger
_CLOSER_TEMPLATES = [
    "Tomorrow morning, don't trust your first thought about {topic_word}. Watch this again instead.",
    "Watch this again and notice {topic_word} in your own life. You'll see everything differently.",
    "Try this for one day. Then watch this again to see what you missed the first time.",
    "Your {topic_word} is lying to you right now. Watch again to see the truth.",
    "Most people ignore this about {topic_word}. Don't be most people. Watch again.",
    "The next time {topic_word} happens, remember this. Watch again to prepare.",
    "You'll forget this in 24 hours. That's your brain protecting you from truth. Watch again tomorrow.",
    "Share this with someone who needs to hear about {topic_word}. They won't listen. But you tried.",
]

# Action words for identity bait hooks
_ACTIONS = [
    "overthink everything", "always feel tired", "constantly worry",
    "never feel good enough", "always procrastinate", "feel empty inside",
    "keep comparing yourself", "always say yes", "fear success",
    "push people away", "feel like an outsider", "always second-guess",
]

# Positive words for contradiction hooks
_POSITIVES = [
    "simple", "straightforward", "easy", "natural", "normal",
    "harmless", "beneficial", "good for you", "what everyone needs",
]

# Conditions for identity bait hooks
_CONDITIONS = [
    "you always pick the quiet corner",
    "you feel everything too deeply",
    "you can't stop thinking",
    "you always feel drained after socializing",
    "you notice everything others miss",
    "you question everything",
    "you always feel like you're pretending",
    "you feel different from everyone",
]

# Negative words for identity bait hooks
_NEGATIVES = [
    "lazy", "weak", "broken", "different", "wrong",
    "sensitive", "too much", "not enough", "crazy",
]

# Topic-specific facts and statistics
_TOPIC_FACTS = {
    "brain": [
        "Your brain uses 20% of your energy but is only 2% of your body weight.",
        "The human brain has approximately 86 billion neurons.",
        "Your brain can process information as fast as 268 mph.",
        "The brain is more active at night than during the day.",
        "Your brain can't feel pain — it has no pain receptors.",
    ],
    "psychology": [
        "95% of your decisions are made by your subconscious mind.",
        "The average person makes 35,000 decisions per day.",
        "Cognitive biases affect everyone, regardless of intelligence.",
        "Your brain processes negative information 5x faster than positive.",
        "Psychological reactions can be measured in as little as 50 milliseconds.",
    ],
    "manipulation": [
        "Narcissists use 7 specific techniques to control others.",
        "Gaslighting works because your brain prefers consistency over truth.",
        "Emotional manipulation activates the same brain regions as physical pain.",
        "Love bombing creates a chemical dependency similar to addiction.",
        "The average person is manipulated 10 times per day without knowing it.",
    ],
    "anxiety": [
        "Anxiety is your brain's ancient alarm system firing at the wrong time.",
        "73% of people experience anxiety that affects their daily life.",
        "Your brain can't distinguish between a bear and a deadline.",
        "Anxiety increases by 40% during uncertain times.",
        "The more you fight anxiety, the stronger it becomes.",
    ],
    "habit": [
        "It takes an average of 66 days to form a new habit.",
        "Your brain forms habits to conserve energy — not to help you.",
        "Habits account for about 40% of your daily actions.",
        "Changing your environment is 2x more effective than willpower.",
        "The habit loop: cue → routine → reward. Break any part to break the habit.",
    ],
    "relationship": [
        "The average person spends 2.5 hours per day thinking about relationships.",
        "Physical touch releases oxytocin within 20 seconds.",
        "Couples who laugh together are 10x more likely to stay together.",
        "The 5:1 ratio: 5 positive interactions for every negative one determines relationship health.",
        "Your attachment style is formed in the first 2 years of life.",
    ],
    "success": [
        "80% of success is showing up consistently.",
        "The most successful people fail 3x more than average.",
        "Your environment determines 80% of your behavior.",
        "Discipline beats motivation 100% of the time.",
        "The first hour of your day determines 60% of your productivity.",
    ],
    "fear": [
        "Your brain processes fear before you're consciously aware of it.",
        "Fear of public speaking ranks higher than fear of death.",
        "Anxiety is fear without a specific target.",
        "Your amygdala can trigger a fear response in 12 milliseconds.",
        "95% of your fears never actually happen.",
    ],
    "social": [
        "Humans are social animals — isolation is perceived as a threat.",
        "You make 11 impressions about someone in the first 7 seconds.",
        "Mirror neurons cause you to unconsciously copy others' emotions.",
        "The average person has 3.5 close friends.",
        "Social rejection activates the same brain regions as physical pain.",
    ],
    "emotion": [
        "Emotions last an average of 90 seconds if you don't feed them.",
        "Your body processes emotions faster than your brain can name them.",
        "Emotional intelligence is 2x more important than IQ for success.",
        "You can't be emotionally intelligent while anxious.",
        "Suppressing emotions increases their intensity by 40%.",
    ],
    "decision": [
        "Your brain makes decisions 6 seconds before you're aware of them.",
        "Decision fatigue causes you to make worse choices as the day goes on.",
        "Most people make decisions based on emotion, then justify with logic.",
        "The average adult makes 35,000 decisions per day.",
        "Analysis paralysis: more options lead to worse decisions.",
    ],
    "identity": [
        "Your self-image is formed by age 7 and rarely changes after that.",
        "You change your personality depending on who you're with.",
        "Your brain creates a narrative to explain decisions you didn't make.",
        "Self-perception is 70% shaped by others' opinions.",
        "The average person spends 30% of their life pretending to be someone else.",
    ],
    "sleep": [
        "Your brain processes emotions during REM sleep.",
        "Lack of sleep reduces IQ by 10 points.",
        "Your brain is more creative when you're tired.",
        "Sleep deprivation affects your immune system more than stress.",
        "The average person needs 7-9 hours of sleep but 35% get less than 6.",
    ],
    "memory": [
        "Your brain can store 2.5 petabytes of information.",
        "Memory is reconstructive — you change it every time you remember it.",
        "Your brain forgets 70% of new information within 24 hours.",
        "Emotional memories are stored differently than factual ones.",
        "The average person remembers only 10% of what they read.",
    ],
    "creativity": [
        "Creative people have more active default mode networks.",
        "Your brain is most creative when you're not trying.",
        "Creativity peaks when you're tired or relaxed.",
        "The average person has 60,000 thoughts per day, but only 5% are creative.",
        "Creative blocks are caused by fear of judgment, not lack of ideas.",
    ],
    "motivation": [
        "Motivation is a result, not a cause.",
        "Your brain releases dopamine BEFORE action, not after.",
        "The 2-minute rule: if it takes less than 2 minutes, do it now.",
        "Willpower is a finite resource that depletes throughout the day.",
        "The most motivated people are the ones who take action without motivation.",
    ],
    "truth": [
        "Your brain lies to you 200 times per day.",
        "The average person can only focus for 8 seconds before losing attention.",
        "Your brain prefers familiar pain over unknown pleasure.",
        "Cognitive biases affect everyone, regardless of IQ.",
        "Your brain processes negative information 5x faster than positive.",
    ],
}


def _get_topic_facts(topic: str) -> list:
    """Get relevant facts for a topic."""
    topic_lower = topic.lower()
    for category, facts in _TOPIC_FACTS.items():
        if category in topic_lower:
            return facts
    # Default facts
    return [
        "Scientists discovered something terrifying about this. They buried it.",
        "Your brain processes this differently than you think.",
        "97% of people don't know this. And it changes everything.",
        "This has been hidden for years. Until now.",
        "The truth will make you uncomfortable. But you need to hear it.",
    ]


def _get_topic_word(topic: str) -> str:
    """Extract the core topic word for template insertion — the most meaningful noun."""
    words = topic.lower().replace("'", "").split()
    # Remove common words and filler
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
            "them", "their", "what", "which", "who", "whom", "these", "those",
            "signs", "secret", "dark", "truth", "trick", "reason", "top",
            "type", "types", "don", "know", "always", "tell", "someone",
            "instantly", "working", "works", "never", "without", "doing",
            "making", "really", "actually", "person", "people"}
    # Preferred topic nouns — these make better template fill-ins
    preferred = [
        "brain", "psychology", "manipulation", "narcissist", "anxiety",
        "habit", "relationship", "success", "fear", "social", "emotion",
        "decision", "identity", "sleep", "memory", "creativity", "motivation",
        "truth", "body", "language", "friendship", "confidence", "empath",
        "procrastinate", "genius", "energy", "time", "money", "happiness",
        "depression", "focus", "mind", "subconscious", "toxic", "trust",
        "control", "power", "love", "lies", "liar", "behavior", "personality",
        "charisma", "brain", "manipulate", "lying", "lies", "betrays",
        "charming", "trap", "cognitive", "bias", "biases", "formula",
        "intelligent", "smart", "lonely", "depress", "overthink",
        "procrastinat", "self", "sabotage", "perfectionist", "people",
        "pleaser", "overthinker", "empath", "narcissistic", "sociopath",
        "gaslight", "toxic", "anxious", "worry", "stressed", "burn",
        "out", "empty", "numb", "disconnect", "isolation", "rejection",
        "psychological", "reason", "signs", "secret", "dark", "truth",
        "trick", "formula", "technique", "method", "strategy", "pattern",
    ]
    
    # First try to find a preferred word
    for pref in preferred:
        for w in words:
            clean = w.strip(".,!?;:'\"")
            if clean == pref or clean.startswith(pref[:5]):
                return clean
    
    # Fall back to longest meaningful word (likely the most important noun)
    meaningful = [w for w in words if w not in skip and len(w) > 4]
    if meaningful:
        # Pick the longest word — likely the most specific noun
        return max(meaningful, key=len)
    
    # Last resort: pick any word > 3 chars
    for w in words:
        if w not in skip and len(w) > 3:
            return w
    
    return "this"


def generate_script_offline(topic: str) -> dict:
    """Generate unique scripts offline using template system."""
    topic_word = _get_topic_word(topic)
    facts = _get_topic_facts(topic)
    
    # Pick random templates
    hook_template = random.choice(_HOOK_TEMPLATES)
    body_set = random.choice(_BODY_TEMPLATES)  # This is a list of 3 paragraphs
    closer_template = random.choice(_CLOSER_TEMPLATES)
    
    # Fill in templates
    hook = hook_template.format(
        topic_word=topic_word,
        positive=random.choice(_POSITIVES),
        action=random.choice(_ACTIONS),
        condition=random.choice(_CONDITIONS),
        negative=random.choice(_NEGATIVES)
    )
    
    body = []
    for paragraph in body_set:
        filled = paragraph.format(
            topic_word=topic_word,
            action=random.choice(_ACTIONS)
        )
        body.append(filled)
    
    closer = closer_template.format(topic_word=topic_word)
    
    # Build full script
    script_text = hook + " " + " ".join(body) + " " + closer
    
    # Generate unique title
    title = _generate_unique_title(topic, hook)
    
    # Generate tags based on topic
    tags = _generate_unique_tags(topic)
    
    # Generate unique description
    description = _generate_unique_description(topic, script_text)
    
    return {
        "title": title,
        "script": script_text,
        "description": description,
        "tags": tags,
        "hook": hook,
        "hook_formula": _detect_hook_formula(hook),
        "sections": ["Hook", "Reveal", "Deep Dive", "Mind-Blow", "Loop Trigger"],
    }


def _generate_unique_title(topic: str, hook: str) -> str:
    """Generate a unique title based on topic and hook."""
    topic_lower = topic.lower()
    
    # Topic-specific title patterns
    title_patterns = {
        "brain": [
            "Your Brain Is Lying To You Right Now",
            "This Brain Hack Changes Everything",
            "Why Your Brain Betrays You Daily",
            "The Dark Truth About Your Brain",
        ],
        "psychology": [
            "Psychology Secret They Buried For Years",
            "This Psychology Trick Works Every Time",
            "Why Psychology Changes How You See Everything",
            "The Dark Psychology Nobody Talks About",
        ],
        "manipulation": [
            "Manipulation Trick Used On You 10x Daily",
            "How To Spot A Manipulator In 10 Seconds",
            "The Manipulation Technique They Don't Want You To Know",
            "Why Manipulators Always Win",
        ],
        "anxiety": [
            "This Anxiety Hack Works In 60 Seconds",
            "Why Your Brain Creates Anxiety For No Reason",
            "The Dark Truth About Anxiety Nobody Tells You",
            "How To Trick Your Brain Out Of Anxiety",
        ],
        "habit": [
            "The Habit Loop You Can't Break",
            "Why Habits Control 40% Of Your Life",
            "The Brain Hack That Changes Habits Instantly",
            "Why You Can't Break Bad Habits",
        ],
        "relationship": [
            "The Friendship Rule That Changes Everything",
            "Why Relationships Fail (According To Psychology)",
            "The Dark Truth About Love Nobody Admits",
            "How To Make Anyone Trust You Instantly",
        ],
        "success": [
            "Why Successful People Think Differently",
            "The Success Myth That's Ruining You",
            "Why Discipline Beats Motivation Every Time",
            "The Dark Secret Behind Every Success",
        ],
        "fear": [
            "Your Fear Is Lying To You",
            "Why Your Brain Creates Fears That Don't Exist",
            "The Dark Truth About Fear Nobody Tells You",
            "How To Trick Your Brain Out Of Fear",
        ],
        "social": [
            "Why Popular People Are Often The Loneliest",
            "The Social Skill That Changes Everything",
            "Why You Always Feel Awkward",
            "The Dark Truth About Social Anxiety",
        ],
        "emotion": [
            "Your Emotions Are Not What You Think",
            "Why Some People Are Naturally Happier",
            "The Dark Side Of Feeling Everything",
            "Why You Always Feel Empty Inside",
        ],
        "decision": [
            "Your Decisions Are Being Controlled",
            "Why You Always Make The Wrong Choice",
            "The Decision Making Bias That Ruins Your Life",
            "How To Make Better Decisions Instantly",
        ],
        "identity": [
            "Why You Don't Really Know Who You Are",
            "The Identity Crisis Nobody Warns You About",
            "Why You Always Feel Like You're Pretending",
            "The Dark Truth About Self Image",
        ],
        "sleep": [
            "Why You Always Wake Up At 3 AM",
            "The Dark Truth About Sleep Nobody Tells You",
            "Why Your Brain Refuses To Shut Off",
            "The Sleep Hack That Changes Everything",
        ],
        "memory": [
            "Why Your Memories Are Probably Fake",
            "The Memory Trick That Changes Everything",
            "Why You Always Forget What You Were About To Say",
            "The Dark Truth About False Memories",
        ],
        "creativity": [
            "Why Creative People Are Often Mentally Ill",
            "The Creativity Hack That Changes Everything",
            "Why You Always Have Your Best Ideas In The Shower",
            "The Dark Side Of Being Creative",
        ],
        "motivation": [
            "Why Motivation Is A Lie",
            "The Motivation Myth That's Ruining You",
            "Why Successful People Don't Need Motivation",
            "The Dark Truth About Motivation Nobody Tells You",
        ],
        "truth": [
            "The Truth They're Hiding From You",
            "Why Your Brain Lies To You 200 Times Per Day",
            "The Dark Truth About Human Nature",
            "Why Most People Live Without Knowing This",
        ],
    }
    
    # Find matching category
    for category, titles in title_patterns.items():
        if category in topic_lower:
            return random.choice(titles)
    
    # Default titles
    default_titles = [
        "This Changes How You See Everything",
        "The Secret Nobody Will Tell You",
        "Your Brain Is Lying To You Right Now",
        "Why 97% Of People Don't Know This",
        "The Dark Truth About Human Nature",
        "This One Thing Changes Everything",
        "Why You've Been Doing This Wrong",
        "The Psychology Trick That Actually Works",
        "Scientists Can't Explain This",
        "Why Smart People Are More Lonely",
    ]
    
    return random.choice(default_titles)


def _generate_unique_tags(topic: str) -> list:
    """Generate unique tags based on topic."""
    topic_words = [w.lower() for w in topic.split() if len(w) > 3][:4]
    base_tags = ["psychology", "mindrank", "facts", "humanbehavior", "mindblown", "shorts"]
    extra_tags = topic_words + ["darkpsychology", "secret", "nevertellyou"]
    return base_tags + extra_tags


def _generate_unique_description(topic: str, script: str) -> str:
    """Generate unique description based on topic."""
    topic_lower = topic.lower()
    
    # Topic-specific descriptions
    desc_templates = {
        "brain": "Your brain is hiding something from you right now... 🧠\n\nFollow @MindRank for more psychology facts nobody talks about.\n\n#psychology #mindrank #facts #humanbehavior #mindblown #shorts #darkpsychology #brain #viral",
        "psychology": "This psychology secret has been hidden for years... 🧠\n\nFollow @MindRank for more psychology facts nobody talks about.\n\n#psychology #mindrank #facts #humanbehavior #mindblown #shorts #darkpsychology #viral",
        "manipulation": "They don't want you to know this manipulation trick... 🎭\n\nFollow @MindRank for more psychology facts nobody talks about.\n\n#psychology #mindrank #facts #humanbehavior #mindblown #shorts #darkpsychology #manipulation #viral",
        "anxiety": "Your anxiety is lying to you right now... 😰\n\nFollow @MindRank for more psychology facts nobody talks about.\n\n#psychology #mindrank #facts #humanbehavior #mindblown #shorts #darkpsychology #anxiety #viral",
        "habit": "This habit trick changes everything... 🔄\n\nFollow @MindRank for more psychology facts nobody talks about.\n\n#psychology #mindrank #facts #humanbehavior #mindblown #shorts #darkpsychology #habits #viral",
        "relationship": "The friendship rule nobody teaches you... 💔\n\nFollow @MindRank for more psychology facts nobody talks about.\n\n#psychology #mindrank #facts #humanbehavior #mindblown #shorts #darkpsychology #relationships #viral",
        "success": "The success myth that's ruining you... 🏆\n\nFollow @MindRank for more psychology facts nobody talks about.\n\n#psychology #mindrank #facts #humanbehavior #mindblown #shorts #darkpsychology #success #viral",
        "fear": "Your fear is lying to you right now... 😱\n\nFollow @MindRank for more psychology facts nobody talks about.\n\n#psychology #mindrank #facts #humanbehavior #mindblown #shorts #darkpsychology #fear #viral",
        "social": "The social skill that changes everything... 👥\n\nFollow @MindRank for more psychology facts nobody talks about.\n\n#psychology #mindrank #facts #humanbehavior #mindblown #shorts #darkpsychology #social #viral",
        "emotion": "Your emotions are not what you think... 💭\n\nFollow @MindRank for more psychology facts nobody talks about.\n\n#psychology #mindrank #facts #humanbehavior #mindblown #shorts #darkpsychology #emotions #viral",
        "decision": "Your decisions are being controlled... 🎯\n\nFollow @MindRank for more psychology facts nobody talks about.\n\n#psychology #mindrank #facts #humanbehavior #mindblown #shorts #darkpsychology #decisions #viral",
        "identity": "Why you don't really know who you are... 🪞\n\nFollow @MindRank for more psychology facts nobody talks about.\n\n#psychology #mindrank #facts #humanbehavior #mindblown #shorts #darkpsychology #identity #viral",
        "sleep": "Why you always wake up at 3 AM... 😴\n\nFollow @MindRank for more psychology facts nobody talks about.\n\n#psychology #mindrank #facts #humanbehavior #mindblown #shorts #darkpsychology #sleep #viral",
        "memory": "Why your memories are probably fake... 🧠\n\nFollow @MindRank for more psychology facts nobody talks about.\n\n#psychology #mindrank #facts #humanbehavior #mindblown #shorts #darkpsychology #memory #viral",
        "creativity": "Why creative people are often mentally ill... 🎨\n\nFollow @MindRank for more psychology facts nobody talks about.\n\n#psychology #mindrank #facts #humanbehavior #mindblown #shorts #darkpsychology #creativity #viral",
        "motivation": "Why motivation is a lie... 🔥\n\nFollow @MindRank for more psychology facts nobody talks about.\n\n#psychology #mindrank #facts #humanbehavior #mindblown #shorts #darkpsychology #motivation #viral",
        "truth": "The truth they're hiding from you... 🔍\n\nFollow @MindRank for more psychology facts nobody talks about.\n\n#psychology #mindrank #facts #humanbehavior #mindblown #shorts #darkpsychology #truth #viral",
    }
    
    # Find matching description
    for category, desc in desc_templates.items():
        if category in topic_lower:
            return desc
    
    # Default description
    return "This changes how you see everything... 🧠\n\nFollow @MindRank for more psychology facts nobody talks about.\n\n#psychology #mindrank #facts #humanbehavior #mindblown #shorts #darkpsychology #viral"


def _detect_hook_formula(hook: str) -> str:
    """Detect which hook formula was used."""
    hook_lower = hook.lower()
    if any(phrase in hook_lower for phrase in ["stop", "wrong", "delete", "incorrect"]):
        return "pattern_interrupt"
    elif any(phrase in hook_lower for phrase in ["everyone thinks", "nobody knows", "secret"]):
        return "contradiction"
    elif any(phrase in hook_lower for phrase in ["they don't want", "hidden", "buried"]):
        return "forbidden_insider"
    elif any(phrase in hook_lower for phrase in ["if you", "you're not", "you're this"]):
        return "identity_bait"
    elif any(phrase in hook_lower for phrase in ["sign", "signal", "reveals"]):
        return "curiosity_gap"
    elif any(phrase in hook_lower for phrase in ["tracked", "tested", "analyzed"]):
        return "specific_transformation"
    elif any(phrase in hook_lower for phrase in ["last", "number", "wait"]):
        return "reveal_teaser"
    return "pattern_interrupt"


def _generate_viral_title(topic: str) -> str:
    """Fallback title generation."""
    return _generate_unique_title(topic, "")


if __name__ == "__main__":
    result = generate_script_offline("The dark psychology trick that works every time")
    print(json.dumps(result, indent=2))
