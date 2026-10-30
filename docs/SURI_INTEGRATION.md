# okkra login pages and recruiter discovery

The production UI lives in `frontend/`. `B2B-app/` is the original design reference and
standalone prototype, not a second API client. Its localStorage identities, simulated speech,
seeded sessions, random feedback, testimonials and business statistics are not used by this app.
Candidate and recruiter login use the same teal palette as the public homepage. `SignInPage.module.css`
scopes login layout to the sign-in wrapper so it cannot affect other routes, including after client-side
navigation. The signed-in UI and public landing share that application design:
sidebar navigation, teal accents, rounded cards and the dark voice-interview screen. Recruiter
features and server-computed progress remain available in that established application shell.

## Routes and feature mapping

| Experience | Integrated behavior |
| --- | --- |
| Candidate sign-in | `/login` (also `/signin`, `/signup`): existing Google OIDC identity and server session |
| Dashboard | `/dashboard`: owned interviews, real usage, coaching tasks and scores; no seeded history |
| Practice setup | `/setup`: saved job briefs, company research, language, duration and professional round selection |
| Live interview | `/interview/[id]`: existing real STT → interviewer → TTS, optional text/camera and device cleanup |
| Feedback | `/report/[id]`: evidence-grounded reports, nullable scores and server-owned rubric |
| Progress | `/progress`: all-time completed/scored totals and drill completion; latest 100 completed sessions for the chart |
| Coaching | `/practice`: existing persistent practice plan, intentionally retains its established URL |
| Candidate discovery | `/opportunities`: opt-in profile, selected resume and request inbox |
| Recruiter sign-in | `/recruiter/login`: the same Google client, with a return destination of `/recruiter` |
| Recruiter directory | `/recruiter`: company onboarding, search by role/headline/location, minimum experience and pagination |
| Recruiter requests | `/recruiter/requests`: pending/approved/declined/revoked state and an approved resume viewer |
| Account and billing | Existing settings, resume library, activity, Stripe checkout and server-owned allowances |

A recruiter is an authenticated Google user who has completed a recruiter profile. A person may
use both candidate and recruiter experiences. This does **not** grant access to private interviews.
Recruiter company names and titles are self-reported; there is no claim of employer verification.
Profile skills and experience are also self-reported. Scores are practice feedback, not verified
hiring readiness. Recruiter discovery makes no AI calls and does not consume interview allowance.

## Consent and storage contract

`app/services/discovery.py` is the authorization and consent boundary. The HTTP layer only parses
contracts and selects directory data. Private account membership is checked on every route.

1. Existing candidates are private by default. No automatic profile creation or migration publish.
2. Publishing requires an owned, shareable resume and a target role. Only the explicitly entered
   name, role, headline, skills, years and location appear in the signed-in recruiter directory.
3. A request records the recruiter's Google name/email, claimed company/title and opportunity
   message. It pins the resume selected at that moment. No email notification is sent.
4. The candidate alone can approve or decline. Approval reveals the uploaded resume's **extracted
   text** and candidate email to that recruiter. It never reveals AI analysis, interviews or scores.
5. Every shared read checks approval, visibility, current resume, candidate membership and ownership.
   Changing the selected resume, withdrawing publication or deleting the upload revokes pending and
   approved requests in the same transaction. Re-publishing does not restore old grants.
6. Candidate mutations and request creation serialize on the candidate profile using a database
   UPDATE, on SQLite and PostgreSQL. A unique candidate/recruiter pair makes repeated requests
   idempotent. Repeated clicks cannot overwrite a denial. Revoked requests can be requested again,
   requiring fresh approval; the inbox shows the latest request for each pair.
7. Recruiter identity details on existing requests are snapshots: editing a company profile does
   not silently change the identity a candidate reviewed. These are not verification records.

Migration `f781c42d930a` adds three tables and nullable `resumes.extracted_text`. New uploads retain
original extracted text privately; PDF binaries are still discarded. Older uploads have only an AI
digest, which cannot be treated as the original resume: the candidate must re-upload before sharing.
Deleting an upload removes its extracted text and hides the linked candidate profile. Historic
interview snapshots retain their existing independent lifecycle. Revocation cannot recall content
already read or saved by a recruiter. No public file URLs or browser credential storage are used.

The directory pages 20 records at a time (API maximum 50). Request inboxes currently show the latest
200 requests. Contact is via the approved email address; scheduling, automated emails, messaging,
shortlists, ATS integrations and employer vetting are not implemented.

## Remaining prototype concepts

- Structured learning courses and personalized content recommendations need a content model and
  authored material. The current practice plan supplies report-driven coaching drills.
- The prototype's difficulty/focus/format chips are not added as inert UI. New practice modes need
  validated agent inputs, appropriate rubrics and quality evaluation before they become controls.
- There is no fabricated STAR score, confidence score, filler-word count, hiring probability or
  guaranteed placement. Current reports expose only supported, evidence-grounded metrics.
- Prototype INR subscription tiers and unlimited promises are not adopted. Existing backend
  allowances and actual configured Stripe checkout remain authoritative.
- Full streaming audio, human calibration of evaluation, recruiter verification and automated
  matching remain separate engineering work. This integration does not pretend they exist.

## Coding-agent entry points

- `frontend/src/components/SignInPage.tsx` and its CSS module: shared candidate/recruiter Google
  sign-in and recovery; all okkra sign-in styling stays here.
- `frontend/src/components/AppShell.tsx`: public route list, protected navigation and role switch.
- `frontend/src/app/{opportunities,recruiter,progress}/`: feature screens, no mock stores.
- `frontend/src/lib/api.ts`: typed requests and CSRF; extend this before adding direct fetch calls.
- `backend/app/services/discovery.py`: consent transitions. Do not bypass this service to share data.
- `backend/app/api/{discovery,progress}.py`: HTTP contracts and owned progress aggregation.
- `backend/tests/test_discovery.py`: privacy, ownership, revocation, duplicate-request concurrency.
- `frontend/e2e/recruiter.e2e.mjs`: real API workflow with isolated test identities, mobile assertions.

Follow `RUN.md` for migrations and test stack commands. Never enable demo authentication in a real
production deployment. The browser identity seeder is test-only and refuses ordinary database URLs.
