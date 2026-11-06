# Browser primitives

- `api.ts` is the only browser API boundary: same-origin `/api`, `credentials: "include"`,
  `X-Requested-With`, CSRF for mutations, typed response contracts and `ApiError`. It also owns
  session discovery and the stable turn request-ID convention.
- `recorder.ts` owns `getUserMedia`, WAV encoding, level metering and resource release. No vendor SDKs.
- `speech.ts` owns cancellable cloud/browser playback and the in-tab audio cache.

Rules: never store tokens or provider keys in localStorage; never call a provider directly; keep
device primitives free of interview business rules; release every stream, recorder and timer on
cancellation and unmount. See `../features/interview/README.md` and `docs/VOICE.md`.
