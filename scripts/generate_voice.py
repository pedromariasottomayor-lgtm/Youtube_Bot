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

SELECTED_VOICE = "en-US-AndrewNeural"  # Most energetic/enthusiastic male voice
SPEECH_RATE    = "+15%"               # Fast = urgency + fits 30-40s sweet spot
SPEECH_PITCH   = "+2Hz"              # Slight lift = more enthusiasm


async def _generate_async(text: str, output_path: str) -> bool:
    """Internal async function to generate speech with sentence-level timestamps."""
    try:
        import edge_tts
        communicate = edge_tts.Communicate(
            text=text,
            voice=SELECTED_VOICE,
            rate=SPEECH_RATE,
            pitch=SPEECH_PITCH
        )
        # Stream to get both audio + timestamps
        submaker = edge_tts.SubMaker()
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
            elif chunk["type"] == "SentenceBoundary":
                submaker.feed(chunk)

        with open(output_path, "wb") as f:
            f.write(audio_data)

        # Save SRT timestamps alongside audio for subtitle sync
        srt_path = output_path.rsplit(".", 1)[0] + ".srt"
        srt_content = submaker.get_srt()
        if srt_content:
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
            log.info(f"Timestamps saved: {srt_path}")

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
