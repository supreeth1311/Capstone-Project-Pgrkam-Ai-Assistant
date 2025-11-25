# services/voice.py
import io
import os
from typing import Optional

from gtts import gTTS
from groq import Groq

# -----------------------
# Groq client (uses GROQ_API_KEY from env / Streamlit secrets)
# -----------------------
_groq_client: Optional[Groq] = None


def _get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        # If GROQ_API_KEY is not explicitly passed, Groq() will read from env
        _groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    return _groq_client


# -----------------------
# Text-to-Speech (gTTS)
# -----------------------
def tts_gtts(text: str, lang_hint: str = "en") -> bytes:
    """
    Return an MP3 byte stream for the given text.
    lang_hint: 'en' | 'hi' | 'pa'
    """
    lang_map = {
        "en": "en",
        "hi": "hi",
        "pa": "pa",  # Punjabi
    }
    lang = lang_map.get((lang_hint or "en").lower(), "en")

    mp3_buf = io.BytesIO()
    tts = gTTS(text=text, lang=lang, slow=False)
    tts.write_to_fp(mp3_buf)
    return mp3_buf.getvalue()


# -----------------------
# Speech-to-Text (ASR) using Groq Whisper
# -----------------------
def transcribe_audio_bytes(audio_bytes: bytes, lang_hint: str = "en") -> Optional[str]:
    """
    Transcribe raw audio bytes to text using Groq Whisper.

    - Expects 'audio_bytes' from streamlit_mic_recorder.
    - Returns transcribed text or None on failure.

    NOTE:
    - Requires `pip install groq`.
    - Uses model "whisper-large-v3" (or "whisper-large-v3-turbo").
    """
    if not audio_bytes:
        return None

    try:
        client = _get_groq_client()

        # Give Groq a fake filename + the raw bytes from mic_recorder
        file_tuple = ("audio.wav", audio_bytes)

        # You can omit 'language' to let Whisper auto-detect.
        # If you want to force language hint, map lang_hint to ["en", "hi", "pa"].
        transcription = client.audio.transcriptions.create(
            file=file_tuple,
            model="whisper-large-v3",  # or "whisper-large-v3-turbo" if you prefer
            response_format="json",
            # language="en",  # optional – uncomment to force English
        )

        # Groq's Python client returns an object with .text field
        text = getattr(transcription, "text", None)
        if not text:
            return None
        return text.strip()

    except Exception as e:
        # For debugging you can temporarily print(e) or log it
        # but in deployed app it's safer to just fail silently
        # and let the UI behave as "no speech detected".
        return None
