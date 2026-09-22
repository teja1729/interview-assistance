# Interview browser feature

`useInterviewSession.ts` coordinates fetching, joining, recording, playback, sending answers and
finishing. The route page renders this state; `CallControls.tsx` contains stateless controls.
The backend remains authoritative for status, remaining time, turn version and transcript.

`InterviewerAvatar.tsx` renders the selected role emblem using the shared icon system. Labels, round,
and icon come from the interview's public `persona_profile` snapshot. Role definitions and behavioral
instructions live in `backend/app/personas.py`; do not duplicate their names in browser lookup tables.

Preserve these contracts when extending the feature:

- The lobby does not start the interview timer. Joining calls the start endpoint.
- A pending answer keeps its request ID and version across network retries. Do not generate a
  fresh ID for a retry: the server uses it to return a previously committed response safely.
- Voice-to-voice is the primary flow. After cloud playback ends, hands-free mode opens the mic.
  At least 500ms of speech-level energy followed by 3s of quiet submits the WAV automatically.
  The speaker and recorder must not overlap. Text entry is an optional fallback.
- Cloud speech failures pause automatic listening and offer audio retry. Never silently fall back
  to the robotic browser voice. Permission denial must allow a user-triggered retry.
- Playback carries the interview ID; the server resolves its saved language and enforces ownership.
  Company facts and their citations render through `components/CompanyContext.tsx`. Search Suggestions
  use a script-free sandboxed frame; never grant it same-origin access or inject its HTML into the page.
- Typed answers reach the API verbatim. Voice answers use a WAV recording and server transcription.
- Deadline and hang-up submit an active recording before ending the session. Recording, playback
  and camera resources must be released on cancellation, permission races and unmount.
- Async work uses generation checks so a disposed session cannot update the replacement screen.
- Ending queues a durable report; the report route polls for completion independently of the call.

`lib/recorder.ts` owns audio resources and WAV encoding. `lib/speech.ts` owns playback cancellation.
Keep these device primitives separate from provider SDKs. Test microphone changes with the fake
device deadline regression in `e2e/saas.e2e.mjs` and the cloud voice scenarios in
`e2e/voice.e2e.mjs`; test server concurrency in backend tests.
