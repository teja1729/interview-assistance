"""Speech transport, format and capability contracts. These tests never call paid services."""

import asyncio
import base64
import io
import json
import wave
from dataclasses import replace

import httpx
import pytest
from fastapi import HTTPException

from app.providers.base import ProviderError
from app.services import sarvam_speech as sarvam
from app.services import speech


@pytest.fixture
def configured(monkeypatch):
    config = replace(speech.settings, audio_provider="sarvam", sarvam_api_key="fixture-key")
    monkeypatch.setattr(speech, "settings", config)
    monkeypatch.setattr(sarvam, "settings", config)
    return config


def test_capabilities_require_the_selected_speech_credential(clients, monkeypatch, configured):
    client = clients()
    assert client.get("/api/capabilities").json() == {"voice_input": True, "cloud_voice": True}
    monkeypatch.setattr(speech, "settings", replace(configured, sarvam_api_key=""))
    assert client.get("/api/capabilities").json() == {"voice_input": False, "cloud_voice": False}
    monkeypatch.setattr(speech, "settings", replace(configured, audio_provider="browser"))
    assert not speech.available()


def test_long_audio_chunks_preserve_every_sample_under_the_rest_limit():
    pcm = b"\x00\x10" * (sarvam.RATE * 65)
    parts = sarvam.chunks(pcm)
    decoded = []
    assert len(parts) == 3
    for part in parts:
        with wave.open(io.BytesIO(part)) as wav:
            assert wav.getnframes() / wav.getframerate() < 30
            decoded.append(wav.readframes(wav.getnframes()))
    assert b"".join(decoded) == pcm


def test_transcription_is_verbatim_ordered_and_concurrency_bounded(monkeypatch, configured):
    client_type = httpx.AsyncClient
    current = maximum = 0

    async def handler(request):
        nonlocal current, maximum
        assert request.headers["api-subscription-key"] == "fixture-key"
        assert b"verbatim" in request.content and b"saaras:v3" in request.content
        current += 1
        maximum = max(maximum, current)
        # Let requests complete out of order; the transcript must retain recording order.
        index = next(i for i in range(5) if f"part-{i}".encode() in request.content)
        await asyncio.sleep((5 - index) * 0.001)
        current -= 1
        return httpx.Response(200, json={"transcript": str(index)})

    monkeypatch.setattr(
        sarvam.httpx, "AsyncClient", lambda **kwargs: client_type(transport=httpx.MockTransport(handler), **kwargs)
    )
    result = asyncio.run(sarvam._transcribe([f"part-{i}".encode() for i in range(5)]))
    assert result == "0 1 2 3 4" and maximum == 3


def test_failed_transcription_never_returns_partial_or_vendor_errors(monkeypatch, configured):
    client_type = httpx.AsyncClient
    monkeypatch.setattr(
        sarvam.httpx,
        "AsyncClient",
        lambda **kwargs: client_type(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(503, json={"error": "private-vendor-content"})
            ),
            **kwargs,
        ),
    )
    with pytest.raises(ProviderError, match="saved for retry") as error:
        sarvam.transcribe(b"\x00\x10" * sarvam.RATE)
    assert "private-vendor-content" not in str(error.value)


def test_tts_uses_operator_voice_and_returns_one_valid_wav(monkeypatch, configured):
    client_type = httpx.Client
    pcm = b"\x00\x10" * 2400
    encoded = base64.b64encode(sarvam.wav_bytes(pcm, 24000)).decode()

    def handler(request):
        body = json.loads(request.content)
        assert body["model"] == "bulbul:v3" and body["speaker"] == "ritu"
        assert body["language_code"] == "en-IN" and body["output_audio_codec"] == "wav"
        return httpx.Response(200, json={"audios": [encoded, encoded]})

    monkeypatch.setattr(
        sarvam.httpx, "Client", lambda **kwargs: client_type(transport=httpx.MockTransport(handler), **kwargs)
    )
    with wave.open(io.BytesIO(speech.synthesize("Tell me about your work."))) as wav:
        assert wav.getframerate() == 24000
        assert wav.readframes(wav.getnframes()) == pcm + pcm


def test_bad_audio_and_silence_never_reach_transcription(monkeypatch, configured):
    def unexpected(*args):
        pytest.fail("Provider must not receive invalid or silent audio")

    monkeypatch.setattr(sarvam, "transcribe", unexpected)
    assert speech.transcribe(sarvam.wav_bytes(b"\0\0" * sarvam.RATE)) == ""
    with pytest.raises(HTTPException) as error:
        speech.transcribe(b"invalid WAV")
    assert error.value.status_code == 400
    with pytest.raises(HTTPException):
        speech.transcribe(sarvam.wav_bytes(b"\x00\x10" * 8000, 8000))
