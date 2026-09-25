# okkra frontend

Read the repository AGENTS.md, then docs/ARCHITECTURE.md and docs/DEVELOPMENT.md.

- `src/lib/api.ts`: typed same-origin requests, CSRF, session discovery and stable turn request IDs.
- `AuthProvider`: session context. `AppShell`: public/private layout and personal account context.
- `/`: public landing. `/login`, `/pricing`: public routes.
- `/dashboard`, `/setup`, `/resumes`: primary preparation flow.
- `/interview/[id]`: interview presentation. `src/features/interview/useInterviewSession.ts` owns
  browser session/device phases; the backend owns the authoritative interview lifecycle. Read
  `src/features/interview/README.md` before changing recording, timers or request retries.
- `/report/[id]`: polls durable report status and supports retry after terminal failure.
- `/practice`, `/activity`, `/settings`, `/billing`: personal account features.
- `lib/recorder.ts`, `lib/speech.ts`: browser device lifecycle; keep vendor reasoning code out.

Use the API client for all mutations. Do not put tokens in localStorage. Voice routing comes from
backend capabilities, with natural cloud playback as the default. No browser model/provider setting
is exposed. See docs/VOICE.md for automatic listening, silence detection and safe audio retries.

`npm run lint`, `npm run typecheck`, `npm run format:check`, `npm run build`, `npm run test:e2e`, `npm run test:voice`.
Build uses Webpack and system fonts, so no font service/network download is needed.

## Login design and recruiter workflow

Candidate and recruiter login use the homepage palette. Keep login-only layout in `SignInPage.module.css`
and shared colors in `globals.css`.
The application retains its original sidebar, teal theme, cards and dark voice
screen. `../B2B-app` remains a separate prototype; do not import its localStorage stores, simulated
speech or feedback engine. Device orchestration stays in `features/interview/useInterviewSession.ts`.

- `/progress`: server-computed progress; never seed history or readiness scores.
- `/opportunities`: candidate opt-in, selected upload, and approval/revocation inbox.
- `/recruiter/login`: shared `SignInPage` configured for recruiter Google return routing.
- `/recruiter`: recruiter onboarding and paginated candidate directory.
- `/recruiter/requests`: approved resume text and email, fetched only through checked APIs.
- `/signin` and `/signup`: candidate sign-in aliases. Recruitment uses `/recruiter/login` explicitly.

Run `npm run test:recruiter` against the isolated stack in RUN.md. See docs/SURI_INTEGRATION.md for
privacy contracts, known scope and the differences from the prototype's unimplemented features.
