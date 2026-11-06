<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

<!-- Project rules. Keep these outside the generated block; `next dev` rewrites only the block above. -->

# okkra frontend rules

Read `README.md` here, then `src/features/interview/README.md` before touching recording, timers,
retries, speech or device cleanup.

- `src/lib/api.ts` is the only browser API boundary: same-origin `/api`, `credentials: "include"`,
  CSRF for mutations, typed contracts and `ApiError`. Never store tokens, provider keys or session
  data in localStorage; never call an AI provider directly.
- The backend owns interview status, remaining time, turn version, transcripts and scores.
  `useInterviewSession.ts` orchestrates device phases only.
- Use persona metadata from `GET /personas` or the interview's `persona_profile`. Do not duplicate
  persona names, icons or behavioral instructions in frontend lookup tables.
- Never inject Company Research `search_suggestions` HTML. Render sourced facts through
  `components/CompanyContext.tsx` and keep any sandboxed frame script-free.
- Run `npm run lint`, `npm run typecheck`, `npm run format:check`, `npm run build`. Use the isolated
  stack in `../RUN.md` for `test:e2e`, `test:voice` and `test:recruiter`.
- `../B2B-app` is an unrelated prototype. Do not import its stores, mock auth or feedback engine.
