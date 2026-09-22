# Domain services

`interviews.py` owns state, versioning and idempotency. `reports.py` owns persistent job claiming and
private stage checkpoints, lease renewal and atomic report/coaching publication. Completed topic
assessments and summary artifacts survive coaching failures. `usage.py` owns database-backed
entitlement counters. `company_research.py` owns bounded Google Search grounding and candidate-scoped
source caches; see `docs/COMPANY_RESEARCH.md`. Search never receives resumes or interview answers.
`speech.py` validates/handles transient audio independently from reasoning providers.
`sarvam_speech.py` owns bounded, ordered transcription chunks and natural voice synthesis.
Read `docs/VOICE.md` before changing audio deadlines, formats or turn-taking behavior.
`billing.py` reconciles current Stripe subscriptions with versioned writes and idempotent event IDs.
`job_descriptions.py` renders structured model output into editable text and saves it through
`setup_cache.py`; cached descriptions/title suggestions avoid inference and quota reservation.
`report_stages.py` runs bounded topic inference with a single checkpoint coordinator.
`assessment.py` validates evidence/rubrics; `practice.py` merges unfinished skills with source links.

Do not hold write transactions while calling a provider. Use a fenced lease for work whose result
will be committed later. Test both duplicate requests and genuinely concurrent requests. The initial
system uses UTC epoch timestamps consistently; do not mix naïve/local datetime fields into comparisons.

`discovery.py` owns explicit candidate publication and recruiter resume consent. It serializes
mutations on the candidate profile, pins a resume to each request, and rechecks every shared read.
Resume deletion must call `revoke_resume` in the same transaction; never expose private resume
models directly to the directory. Original extracted text is distinct from the model-generated
digest. Recruiter company details are self-reported. See docs/SURI_INTEGRATION.md.
