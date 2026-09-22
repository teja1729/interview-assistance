# Voice-to-voice interviews

Normal operation uses `AUDIO_PROVIDER=sarvam`, `saaras:v3` for transcription and `bulbul:v3`
with the `ritu` voice for interviewer speech. Credentials and voice choices are server-owned
in `backend/.env`; the six reasoning agents remain routed by `backend/config/models.toml`.
Change `SARVAM_TTS_VOICE` to another supported Bulbul v3 speaker and restart the API to change
the voice. `SPEECH_LANGUAGE=en-IN` supplies a fallback output language; setup now saves an explicit interview
language shared by planning, follow-ups and TTS. Input language is detected.

## Conversation lifecycle

1. Join starts the server timer and plays the first question using cloud audio.
2. Once playback finishes, hands-free mode requests microphone permission and records an answer.
3. The browser detects speech-level energy, then waits for three seconds of quiet to submit.
   **Send answer** submits immediately. **Hands-free off** uses manual answer controls.
4. The API validates and transcribes the WAV, runs the interviewer, and stores the turn.
5. The next reply plays aloud, then listening resumes. Captions/transcripts and typing are optional.

This is sequential turn-taking, not full-duplex streaming or interruption handling. End-of-turn
detection uses signal energy (500ms above the threshold), not semantic speech detection. Background
noise can delay automatic submission; use Send answer in that case. The recorder and speaker do
not intentionally overlap. Recordings stop at five minutes or at the interview deadline.

## Failure behavior

- Cloud audio failures pause listening and expose **Retry question audio**. They do not silently
  switch to browser speech. The latest audio blob is cached in the tab to retry playback without
  paying for synthesis again; navigating away releases that in-memory reference.
- Permission denial offers **Retry microphone** after the user updates browser site permissions.
  Missing devices and system-level blocks have separate messages. HTTPS or localhost is required.
- Transcription/turn failures retain the WAV and idempotency key in the current tab for retry.
  Reloading discards an unsent recording. The server never stores raw audio.
- An installation explicitly using `AUDIO_PROVIDER=browser` has typed input and local speech.
  It does not advertise microphone support. Tests use this mode to avoid paid calls.

## Adapter contracts

`services/speech.py` validates 16kHz mono 16-bit WAV, rejects oversized/invalid recordings, and
ignores silence before dispatch. `services/sarvam_speech.py` contains only Sarvam transport.
Its REST transcription chunks longer answers at quiet boundaries under 30 seconds, keeps all
samples in order, and allows three concurrent requests within one 30-second overall deadline.
Any failed chunk fails the whole transcript. The existing 150-second turn lease covers this
budget plus the bounded reasoning calls. Chunking can split a spoken word when no quiet boundary
exists; keep input audio clear and review live transcription quality before changing thresholds.

Synthesis decodes and validates returned WAV audio and merges multiple clips into one WAV.
Bulbul output is 24kHz mono PCM. The API keeps credentials and raw vendor errors off the client.

## Verification

`uv run pytest tests/test_speech.py` tests wire format, WAV chunking, ordering, concurrency limits,
failure sanitization and capabilities without paid calls. `npm run test:voice` runs browser tests
with fake devices and intercepted APIs, covering automatic turns, permissions, cleanup and voice
outage recovery. `npm run test:e2e` retains the full interview and deadline regression.

Official transport references:
- https://docs.sarvam.ai/api-reference/speech-to-text/transcribe
- https://docs.sarvam.ai/api-reference/text-to-speech/convert

Playback sends the interview ID, and /tts resolves its candidate-owned saved language. English and
ten Indian language choices follow [Sarvam language codes](https://docs.sarvam.ai/api/api-guides-tutorials/text-to-speech/how-to/set-the-language).
The browser audio cache includes session/language so retries cannot replay another context.
