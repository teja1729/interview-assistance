"""Native Sarvam speech transport. Credentials and voices are server-owned.

REST transcription accepts at most 30 seconds. Split longer PCM at quiet boundaries,
preserve sample order, and send at most three chunks concurrently within one 30-second
deadline. This leaves room for the interviewer inside its 150-second turn lease.
No recordings are written to disk and no failed chunk becomes a partial transcript.
"""

import asyncio
import base64
import io
import wave
from array import array

import httpx

from ..config import settings
from ..providers.base import ProviderError
from ..schemas import Transcript

RATE = 16000


def wav_bytes(pcm: bytes, rate=RATE) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm)
    return output.getvalue()


def chunks(pcm: bytes) -> list[bytes]:
    """Prefer a quiet 100ms window near 29s, without dropping/duplicating PCM samples."""
    result = []
    while len(pcm) > 29 * RATE * 2:
        samples = array("h", pcm[: 29 * RATE * 2])
        width = RATE // 10
        # Equal-energy windows prefer the latest cut to avoid unnecessarily small chunks.
        start = min(
            range(24 * RATE, 29 * RATE - width + 1, width),
            key=lambda i: (sum(s * s for s in samples[i : i + width]), -i),
        )
        cut = (start + width // 2) * 2
        result.append(wav_bytes(pcm[:cut]))
        pcm = pcm[cut:]
    if pcm:
        result.append(wav_bytes(pcm))
    return result


async def _transcribe(parts: list[bytes]) -> str:
    semaphore = asyncio.Semaphore(3)
    async with asyncio.timeout(30), httpx.AsyncClient(timeout=20) as client:

        async def one(part):
            async with semaphore:
                response = await client.post(
                    "https://api.sarvam.ai/speech-to-text",
                    headers={"api-subscription-key": settings.sarvam_api_key},
                    data={"model": settings.sarvam_stt_model, "mode": "verbatim", "language_code": "unknown"},
                    files={"file": ("answer.wav", part, "audio/wav")},
                )
                response.raise_for_status()
                return Transcript(text=response.json()["transcript"]).text.strip()

        # TaskGroup cancels siblings on any failure; never leak unfinished HTTP work.
        async with asyncio.TaskGroup() as group:
            tasks = [group.create_task(one(part)) for part in parts]
        return Transcript(text=" ".join(task.result() for task in tasks if task.result())).text


def transcribe(pcm: bytes) -> str:
    try:
        return asyncio.run(_transcribe(chunks(pcm)))
    except Exception as exc:
        raise ProviderError("Speech transcription failed. Your recording is saved for retry in this tab.") from exc


def synthesize(text: str, language: str | None = None) -> bytes:
    try:
        with httpx.Client(timeout=20) as client:
            response = client.post(
                "https://api.sarvam.ai/text-to-speech",
                headers={"api-subscription-key": settings.sarvam_api_key},
                json={
                    "text": text,
                    "language_code": language or settings.speech_language,
                    "model": settings.sarvam_tts_model,
                    "speaker": settings.sarvam_tts_voice,
                    "pace": 1.0,
                    "speech_sample_rate": 24000,
                    "output_audio_codec": "wav",
                },
            )
            response.raise_for_status()
            audios = response.json()["audios"]
        if not audios:
            raise ValueError("Missing speech audio")
        frames = []
        for encoded in audios:
            with wave.open(io.BytesIO(base64.b64decode(encoded, validate=True))) as wav:
                if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, 24000):
                    raise ValueError("Unsupported speech format")
                frames.append(wav.readframes(wav.getnframes()))
        if not any(frames):
            raise ValueError("Empty speech audio")
        return wav_bytes(b"".join(frames), 24000)
    except Exception as exc:
        raise ProviderError("The interviewer voice is unavailable. Retry the question audio.") from exc
