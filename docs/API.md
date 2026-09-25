# API contract

The browser accesses `/api` on the same origin as Next.js. The reverse proxy forwards to FastAPI.
All private endpoints require `interview_session` (HTTP-only). POST/PUT/PATCH/DELETE also require
`X-CSRF-Token` from `/api/auth/me` and an allowed Origin (or the non-browser
`X-Requested-With: interview-studio` header). The signed Stripe webhook is exempt from CSRF.

| Group | Routes |
| --- | --- |
| Public | GET /health, /ready, /auth/config; GET /auth/google, /auth/google/callback, /auth/linkedin, /auth/linkedin/callback |
| Sessions | GET /auth/me; POST /auth/demo (development only), /auth/logout, /auth/logout-all |
| Resumes | GET/POST /resumes; GET/DELETE /resumes/{id} |
| Interviews | GET/POST /interviews; GET /interviews/{id}; POST /interviews/{id}/join, /turn-text, /turn, /finish, /abandon |
| Practice | GET /practice; PATCH /practice/{id} |
| Visibility | GET /agent-runs, /capabilities, /personas |
| Helpers | POST /suggest/titles, /suggest/job-description, /company-research, /tts |
| Billing | GET /billing; POST /billing/checkout, /billing/portal, /billing/webhook |

`GET /auth/me` returns `{user, account: {id, plan}, csrf_token, demo}`. Workspace management,
invitations, switching and provider-preference routes are retired and return 404. All candidate
resources and traces are scoped to the signed-in user. Billing offers Starter and Pro personal plans.

`POST /suggest/job-description` accepts `job_title`, `company`, and `experience_years` and returns
`{job_description, demo}`. The text contains overview, responsibilities, requirements, optional skills
and first-90-day outcomes. `demo` is false in normal operation; isolated fixture tests are explicitly
marked in both the response metadata and rendered text. Generated descriptions are editable practice
context, not verified employer vacancies.

## Critical request shapes

`GET /personas` returns four public role definitions with `id`, `name`, `round`, `description`,
`approach`, `focus` (a list of labels), and `icon`. Behavioral instructions are server-only.
`POST /interviews` accepts `persona` as `recruiter`, `hiring_manager` (default), `technical`, or
`leadership`. Legacy values `neutral`, `friendly`, `tough`, and `company` remain accepted and map
to the new roles; unknown IDs return 422. Interview responses include `persona_profile` with the
public definition snapshotted at creation. Render its name and icon instead of maintaining a second
frontend role map. Older interviews resolve their profile through the legacy alias mapping.

`POST /interviews/{id}/turn-text`:

```json
{"text":"My exact answer", "version":1, "request_id":"a-new-UUID-for-this-answer"}
```

WAV turns carry multipart `audio`, `version`, `request_id`. Reuse the same ID and same content
when retrying an uncertain network result. Do not generate a new ID for a retransmission.

A turn response includes transcript, reply, done, repeat, remaining_seconds and new version.
`repeat=true` keeps the question open and does not store an answer. A 409 requires recovery from
a saved response or the latest server session, not blind overwrite.

`POST /finish` returns an Interview. `status=finishing` means a durable job exists, not that a
report is ready. Poll GET /interviews/{id}. `finished` includes the validated report;
`report_failed` permits explicit POST /finish retry. Duplicate finish requests share one job.

Lists have bounded sizes. Interview history supports limit (max 100) and offset. Agent activity
returns the latest 100 entries; practice returns up to 200 tasks. Extend pagination contracts before
using these endpoints for unbounded analytics.

## Error semantics

- 400 / 422: bad file, empty answer, invalid contract, or invalid state input.
- 401: session absent/expired; sign in again.
- 403: CSRF/origin/account ownership failure.
- 404: resource absent **or outside the caller's authorized scope**.
- 409: concurrent operation, stale version, or unavailable state transition.
- 429: account usage/rate limit exhausted.
- 503: unavailable provider or unconfigured external integration.

Provider errors are sanitized. Correlate X-Request-ID and trace metadata for diagnosis. Use
`/api/openapi.json` for exact request validation, and `frontend/src/lib/api.ts` for browser response types.

## Company research, language and report progress

`POST /company-research` accepts `company`, `job_title`, and optional HTTPS `company_url`. Returns
`{id, company, status, facts, sources, researched_at, note, search_suggestions}`. `status` is researched
or unavailable; an unavailable result contains no invented facts. Cache IDs are candidate-owned.
Facts refer to source IDs. Render source links and sandbox Search Suggestions HTML; do not inject it.

`POST /interviews` additionally accepts `company_url`, `company_research_id` and `language` (one of
`en-IN`, `hi-IN`, `bn-IN`, `ta-IN`, `te-IN`, `gu-IN`, `kn-IN`, `ml-IN`, `mr-IN`, `pa-IN`, `od-IN`).
Missing explicit language defaults to English or a supported language requested in legacy free-text
instructions. Research is resolved automatically when a company is supplied. A mismatched cached
research ID returns 409; another candidate's ID returns 404. Interview responses expose `language`,
`company_context` and optional `report_progress: {completed_steps, label, error}`. Private execution
bundles, shared briefs and job checkpoints are never returned.

`POST /suggest/job-description` accepts the same optional research URL/ID and returns company_context
alongside the existing description/demo fields. Generated text remains a practice brief.

`POST /tts` accepts text plus optional interview_id. The saved interview language takes precedence,
and the interview must belong to the signed-in candidate. Without an ID, optional language selects a
supported language; omitted language uses the configured default. Changing language does not select
a provider/model. New report question objects add rubric components and answer-attributed evidence_refs;
existing reports retain their historical shape.

## Recruiter discovery and progress

All endpoints below require a database session and current account membership. Mutations require
CSRF and the existing origin checks. See [SURI_INTEGRATION.md](SURI_INTEGRATION.md) for consent rules.

| Method and path | Contract |
| --- | --- |
| `GET /api/progress` | Candidate-owned all-time interview/drill totals, per-round averages, latest 100 completed sessions |
| `GET /api/recruiter/profile` | Current user's company/title or null; no role inferred from a query parameter |
| `PUT /api/recruiter/profile` | `{company_name, job_title}`; enrol/update the authenticated recruiter |
| `GET /api/recruiter/candidates` | Enrolled recruiters only; `q`, `min_experience`, `offset`, `limit`; returns `{items,total}` |
| `GET /api/candidate-profile` | Own editable profile or null |
| `PUT /api/candidate-profile` | Full replacement of display_name, headline, target_role, location, experience_years, skills, discoverable, resume_id |
| `POST /api/recruiter/candidates/{id}/request` | `{message}`; 10–1500 characters; self-requests and unpublished candidates rejected |
| `GET /api/recruiter/requests` | Current recruiter's latest 200 requests, candidate name and status |
| `GET /api/candidate-requests` | Own latest 200 incoming requests with recruiter identity snapshot |
| `PATCH /api/candidate-requests/{id}` | `{status: approved\|denied\|revoked}`; only the owning candidate can decide |
| `GET /api/recruiter/requests/{id}/resume` | Approved requester only: candidate_name, email, resume_name, original extracted text |

Published previews contain no account IDs, email, resume ID, original text, digest, scores or
interview history. Requests expose a resume only through the checked sharing endpoint. Resume lists
now include `shareable`; uploads predating extracted-text retention must be re-uploaded to share.
