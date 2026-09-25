# Product and code assessment

## Product thesis

okkra helps a candidate turn their actual experience into clearer interview answers.
The core loop is resume + target role → practice → evidence-based feedback → focused exercises
→ another practice session. That loop is the product hypothesis to validate with real candidates.

Candidate-specific questions, quoted evidence and follow-through on practice tasks give users a
concrete reason to return. Personal accounts keep preparation focused on the individual candidate.
Operator-managed model routing and the agent architecture support the product but are not
substitutes for useful feedback.

## Risks to validate

- A fluent report can still give incorrect technical advice. Review live reports against expert
  assessments; schema validation proves format, not correctness.
- Job search may be episodic. Measure whether users return to practice after reading a report.
- Scores can look more precise than they are. Keep practice bands and evidence visible; calibrate
  scoring against a reviewed sample before making stronger outcome claims.
- Sequential speech processing can interrupt conversation. Measure transcription, first question,
  answer-to-next-question and report latency separately before choosing a voice roadmap.
- Hosting, inference and support costs depend on actual usage. Measure spend per completed session
  before setting paid prices. The repository intentionally leaves Stripe prices operator-configured.

Useful initial measures: first-session completion, second-session return, practice-task completion,
report retry/error rate, evidence-quote accuracy and latency by provider/prompt version. These are
proposed validation measures, not claims that the application already collects analytics.

## Code assessment

The SaaS implementation separates HTTP/auth, domain services, agent prompts/contracts, provider
adapters and persistence. Tenant ownership, CSRF, quotas, turn versions, idempotency and worker
leases are enforced in code rather than prompts. PostgreSQL and SQLite contract tests cover these
boundaries; browser tests cover the full candidate workflow and recording cleanup.

The browser session/device hook is separate from the interview page. New agents and providers
have explicit extension recipes, and migrations preserve schema history. This makes the main
changes discoverable for coding agents without requiring them to infer undocumented coupling.

Remaining launch work includes live-model quality evaluation, a completed Google consent flow,
Stripe test-mode checkout validation, deployment/container verification, backup/restore testing,
and published retention/privacy/support policies. Account self-deletion, automated retention,
real-time bidirectional voice remain future features. See SECURITY.md
and DEPLOYMENT.md for the exact operational boundaries.
