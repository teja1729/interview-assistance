"""Speech is independent of the reasoning provider. Audio is processed transiently, never retained."""

import io
import math
import wave
from array import array

from fastapi import HTTPException

from ..config import settings
from . import sarvam_speech


def available():
    """Capability discovery checks configuration presence, not a paid vendor probe."""
    return settings.audio_provider == "sarvam" and bool(settings.sarvam_api_key)


def transcribe(raw):
    if not available():
        raise HTTPException(503, "Voice transcription is not configured. Type your answer instead.")
    try:
        with wave.open(io.BytesIO(raw)) as wav:
            if wav.getsampwidth() != 2 or wav.getnchannels() != 1 or wav.getframerate() != 16000:
                raise HTTPException(400, "Use 16 kHz mono 16-bit WAV audio")
            if wav.getnframes() / wav.getframerate() > 300:
                raise HTTPException(400, "Answers must be under five minutes")
            frames = wav.readframes(wav.getnframes())
        samples = array("h", frames)
        if not samples or math.sqrt(sum(x * x for x in samples) / len(samples)) / 32768 < 0.004:
            return ""
    except (wave.Error, EOFError, ValueError) as exc:
        raise HTTPException(400, "Invalid WAV recording") from exc
    if settings.audio_provider == "sarvam":
        return sarvam_speech.transcribe(frames)
    raise HTTPException(503, "Voice transcription is not configured. Type your answer instead.")


def synthesize(text, language="en-IN"):
    if not available():
        raise HTTPException(503, "Cloud speech is not configured; use the browser voice")
    if settings.audio_provider == "sarvam":
        return sarvam_speech.synthesize(text, "en-IN")
    raise HTTPException(503, "Cloud speech is not configured; use the browser voice")
