# services/voice.py
import io
import os
import tempfile
from typing import Optional

from gtts import gTTS

# -----------------------
# Text-to-Speech (gTTS)
# -----------------------
def tts_gtts(text: str, lang_hint: str = "en") -> bytes:
    """
    Return an MP3 byte stream for the given text.
    lang_hint: 'en' | 'hi' | 'pa'
    """
    lang_map = {"en": "en", "hi": "hi", "pa": "pa"}
    lang = lang_map.get((lang_hint or "en").lower(), "en")

    mp3_buf = io.BytesIO()
    tts = gTTS(text=text, lang=lang, slow=False)
    tts.write_to_fp(mp3_buf)
    return mp3_buf.getvalue()

# -----------------------
# Speech-to-Text (Groq Whisper)
# -----------------------
def _whisper_lang(lang_hint: str) -> Optional[str]:
    """
    Map 'en'|'hi'|'pa'|'auto' -> Whisper language codes (None for auto).
    """
    if not lang_hint:
        return None
    h = lang_hint.lower()
    if h in {"auto", "detect"}:
        return None
    if h in {"en", "hi", "pa"}:
        return h
    # default to auto if unknown
    return None

def transcribe_audio_bytes(audio_bytes: bytes, lang_hint: str = "auto") -> Optional[str]:
    """
    Transcribe raw audio bytes using Groq Whisper API.
    Requires:
      pip install groq
      env var GROQ_API_KEY set
    Returns stripped text or None on failure.
    """
    if not audio_bytes:
        return None

    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        # No key → gracefully return None (UI just won't prefill)
        return None

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        # Write bytes to a temporary WAV file for upload
        # (streamlit-mic-recorder usually yields WAV bytes)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()

            language = _whisper_lang(lang_hint)  # None => auto-detect
            # Groq Whisper models: "whisper-large-v3" (multilingual), "distil-whisper-large-v3-en" (English)
            model_name = "whisper-large-v3" if language is None or language != "en" else "distil-whisper-large-v3-en"

            with open(tmp.name, "rb") as f:
                resp = client.audio.transcriptions.create(
                    file=f,
                    model=model_name,
                    # language can be omitted for auto; pass only if specified
                    **({"language": language} if language else {}),
                    # You can request plain text
                    response_format="text"
                )

        # `resp` is a string when response_format="text"
        text = (resp or "").strip()
        return text or None

    except Exception:
        # Any error (network/format/rate limits) → fail silently; UI remains ok
        return None
