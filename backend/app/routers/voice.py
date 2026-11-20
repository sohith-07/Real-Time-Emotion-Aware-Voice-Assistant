"""Voice router.

The browser's Web Speech API performs ASR (SpeechRecognition) and TTS
(SpeechSynthesis) client-side. This router provides:

  * ``GET /api/voice/info`` - capabilities and default settings the
    frontend uses to configure the Web Speech API.
  * ``GET /api/voices`` - placeholder list (the real list is built in the
    browser from ``speechSynthesis.getVoices()`` because voices are
    device-specific).
  * ``GET /api/voice/tts?text=...`` - *optional* server-side TTS using gTTS
    if installed. Returns an MP3 audio stream. Use this only if the Web
    Speech API is unavailable in the user's browser. 503 otherwise.
"""
from __future__ import annotations

import io

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..config import settings

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.get("/info")
def voice_info() -> dict:
    """Information the frontend uses to configure client-side ASR/TTS."""
    return {
        "asr_engine": "web_speech_api",
        "tts_engine": "web_speech_api",
        "server_tts_available": _gtts_available(),
        "default_language": "en-US",
        "supported_emotions": [
            "joy", "sadness", "anger", "fear", "surprise", "neutral", "disgust",
        ],
        "emotion_to_voice_hint": {
            "joy": {"rate": 1.1, "pitch": 1.2},
            "sadness": {"rate": 0.9, "pitch": 0.8},
            "anger": {"rate": 1.05, "pitch": 0.9},
            "fear": {"rate": 1.0, "pitch": 1.1},
            "surprise": {"rate": 1.15, "pitch": 1.3},
            "neutral": {"rate": 1.0, "pitch": 1.0},
            "disgust": {"rate": 0.95, "pitch": 0.85},
        },
        "note": (
            "Voice I/O is performed in the browser via the Web Speech API. "
            "Chrome, Edge and Safari provide the most reliable support. "
            "Firefox has limited SpeechRecognition support."
        ),
    }


@router.get("/voices")
def list_voices() -> dict:
    """Stub endpoint. Real voices come from the browser."""
    return {
        "voices": [],
        "note": (
            "Voice names are device-specific and discovered at runtime in the "
            "browser via window.speechSynthesis.getVoices()."
        ),
    }


def _gtts_available() -> bool:
    try:
        import gtts  # type: ignore  # noqa: F401
        return True
    except Exception:
        return False


@router.get("/tts")
def server_tts(
    text: str = Query(..., min_length=1, max_length=1000),
    lang: str = Query("en", max_length=10),
) -> StreamingResponse:
    """Optional server-side TTS using gTTS (returns MP3 audio).

    Only use this if the browser has no SpeechSynthesis support. Requires
    the optional ``gTTS`` package and an internet connection.
    """
    if not _gtts_available():
        raise HTTPException(
            status_code=503,
            detail=(
                "Server-side TTS is unavailable. Install gTTS (pip install gTTS) "
                "or use the browser's Web Speech API (SpeechSynthesis)."
            ),
        )
    try:
        from gtts import gTTS  # type: ignore

        tts = gTTS(text=text, lang=lang)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return StreamingResponse(buf, media_type="audio/mpeg")
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Server-side TTS failed: {exc}",
        ) from exc
