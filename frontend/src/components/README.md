# Shared presentation

- `AppShell.tsx` owns public/private routing UX, candidate/recruiter navigation and sign-out. It is a
  UX guard only; the backend remains authoritative for authorization.
- `AuthProvider.tsx` exposes the session and reacts to the `session-expired` event.
- `SignInPage.tsx` / `SignInPage.module.css` hold login-only layout shared by candidate and recruiter
  routes.
- `CompanyContext.tsx` renders sourced company facts and citations. Never inject
  `search_suggestions` HTML; keep Search Suggestions in a script-free sandbox.
- `Icon.tsx` is the shared icon set referenced by personas and navigation.
- `ScoreChart.tsx` renders progress history. `Nav.tsx` is a compatibility re-export of `Brand`;
  `ModeTabs.tsx` selects voice interview or text topic practice on setup.

Rules: consume server metadata (personas, capabilities, plans) instead of duplicating it; keep
credentials and provider state out of the browser; do not encode authorization decisions here.
