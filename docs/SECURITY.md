# Security boundaries and current limits

## Implemented controls

- Google and LinkedIn OIDC authorization-code sign-in using Authlib, state/nonce and verified email claims.
- Identity keyed by provider plus subject. No automatic account linking by email.
- Opaque session cookies: HTTP-only, SameSite=Lax, Secure in production. Token hashes are stored
  in the database. Every authenticated mutation checks a per-session CSRF token.
- Exact-origin checks on browser writes; explicit header for non-browser clients. CORS is scoped
  to the configured origin. Authentication and membership are checked for every private route.
- Resumes, interviews, practice tasks and execution traces are candidate-private, including for
  legacy container owners. Models are operator-configured in code, with no browser preference API.
- Explicit candidate publication exposes only selected profile fields to signed-in recruiters.
  Resume text and email require candidate approval, with ownership and consent checked on every read.
  Withdrawing publication, changing the selected resume or deleting it revokes access transactionally.
- Workspace creation, switching, invitations and member administration are retired. Existing
  container records are preserved for history and billing compatibility; sign-out-all revokes sessions.
- Request/file bounds, WAV validation, strict model contracts, bounded inference, atomic usage limits.
- Prompt/data separation, no model-accessible execution tools, and deterministic transition policy.
- Signed Stripe webhook processing with idempotent event IDs and server-controlled entitlements.
- No secrets or raw provider exception messages in browser responses or agent activity records.
- Development demo auth/provider are rejected at production startup.

## Data handling

Resume PDF binaries and audio are processed transiently. New resume uploads retain their original
extracted text privately for approved recruiter sharing, alongside AI digests, transcripts and reports
in the database. Existing interviews retain their resume snapshot after deleting a
library entry. Camera preview stays in the browser. Configured AI vendors receive the context
needed for their task; operators must review their account's retention/data-use settings.

## Operator work before public launch

Configure OAuth and HTTPS; use a secret manager and a least-privilege DB account; configure backup
and restore testing; define retention/deletion/export handling and publish an accurate privacy policy.
Place public endpoints behind an edge proxy with request-size limits and appropriate abuse controls.
Logs and backups need restricted access. Set model/vendor spend limits independently of app quotas.

## Explicit limitations

- No automated account self-deletion, retention scheduler, email delivery, SSO/SCIM or organization
  domain verification. The product uses personal accounts; old invitation URLs redirect to Account.
- No database RLS: isolation is enforced in the service/API layer with tests. Add RLS as defense
  in depth if your operating model requires direct tenant database access.
- No antivirus/OCR pipeline. Only text-based PDFs and UTF-8 text are supported; encrypted/oversized
  PDFs are rejected. Run CPU-heavy extraction in a constrained worker if public upload volume grows.
- No claim that scores predict employment outcomes. Live-model quality and fairness need separate evaluation.
- Recruiter company/title and candidate skills/experience are self-reported. Employer verification,
  automated matching and email notifications are not implemented. Revocation blocks future access;
  it cannot recall content already read or copied. See [okkra sign-in and discovery](SURI_INTEGRATION.md).
- Session lifetime is 30 days with explicit revocation; there is no device-management UI beyond sign-out-all.

Report problems privately to the operator; do not paste access tokens or candidate documents into
public issue trackers. Add a focused regression test whenever a boundary defect is corrected.
