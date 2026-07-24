"""
Step 2: Generate voiceover using FREE Microsoft Edge TTS
No API key needed - uses edge-tts Python library (free, unlimited)
Install: pip install edge-tts
"""

import asyncio
import logging
import os

log = logging.getLogger(__name__)

# ─── VOICE OPTIONS (all free) ─────────────────────────────────────
# More voices: run `edge-tts --list-voices` in terminal
VOICES = {
    "male_us":     "en-US-GuyNeural",        # US male - natural
    "female_us":   "en-US-JennyNeural",      # US female - friendly
    "male_uk":     "en-GB-RyanNeural",       # UK male - professional
    "female_uk":   "en-GB-SoniaNeural",      # UK female - clear
    "male_au":     "en-AU-WilliamNeural",    # Australian male
}

SELECTED_VOICE = VOICES["male_us"]   # ← Change this to pick a different voice
SPEECH_RATE    = "+0%"               # Speed: "-10%" slower, "+10%" faster
SPEECH_PITCH   = "+0Hz"             # Pitch: "-5Hz" lower, "+5Hz" higher


async def _generate_async(text: str, output_path: str) -> bool:
    """Internal async function to generate speech."""
    try:
        import edge_tts
        communicate = edge_tts.Communicate(
            text=text,
            voice=SELECTED_VOICE,
            rate=SPEECH_RATE,
            pitch=SPEECH_PITCH
        )
        await communicate.save(output_path)
        size_kb = os.path.getsize(output_path) / 1024
        log.info(f"Voiceover saved: {output_path} ({size_kb:.1f} KB)")
        return True
    except ImportError:
        log.error("edge-tts not installed. Run: pip install edge-tts")
        return False
    except Exception as e:
        log.error(f"Voiceover generation error: {e}")
        return False


def generate_voiceover(script: str, output_path: str) -> bool:
    """
    Generate MP3 voiceover from script text.
    
    Args:
        script: The text to convert to speech
        output_path: Where to save the MP3 file
    Returns:
        True if successful, False otherwise
    """
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    return asyncio.run(_generate_async(script, output_path))


# ─── FALLBACK: gTTS (Google TTS - also free) ─────────────────────
def generate_voiceover_gtts(script: str, output_path: str) -> bool:
    """
    Alternative: Use gTTS if edge-tts doesn't work.
    Install: pip install gTTS
    """
    try:
        from gtts import gTTS
        tts = gTTS(text=script, lang="en", slow=False)
        tts.save(output_path)
        log.info(f"gTTS voiceover saved: {output_path}")
        return True
    except ImportError:
        log.error("gTTS not installed. Run: pip install gTTS")
        return False
    except Exception as e:
        log.error(f"gTTS error: {e}")
        return False


if __name__ == "__main__":
    # Test the voiceover
    test_script = "Hello! This is a test of the automatic voiceover system. It works completely for free!"
    success = generate_voiceover(test_script, "output/test_voice.mp3")
    print("Success!" if success else "Failed - check logs above")
