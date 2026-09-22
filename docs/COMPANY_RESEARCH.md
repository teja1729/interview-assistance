# Company research

A company name resolves saved company research during setup, before planning. A cache miss or explicit refresh
triggers a bounded Google Search grounding call.
The candidate can preview research with **Research company**, or let JD generation/interview creation
resolve it automatically. An optional official company/job URL narrows identification. A missing,
ambiguous or unavailable search result remains visibly unavailable; it never becomes invented facts.

## Transport and contracts

`services/company_research.py` uses the shared runtime through the seventh `company_research` role.
Its profile must declare `search` capability and its adapter must implement search. Gemini
`google_search` is the current adapter, with a 35-second total deadline, 30-second attempt timeout,
at most two runtime attempts, no nested SDK retries, and 2,400 output tokens. The default search
profile is `gemini_search` (`gemini-2.5-flash`), configured in models.toml. Only company name, role and optional
public URL go to search. Resume content, candidate names, custom instructions and answers do not.

Facts are extracted only from response segments linked to grounding sources, and require evidence
that a web query occurred. URLs must be public HTTPS domain URLs without credentials. The application
does not crawl arbitrary URLs from its own network. When a company URL is supplied, sources are
restricted to its domain using the source URI or Google's source-domain title for opaque redirect
links. Unidentifiable source origins are omitted. Without a URL, the search prompt requests official
sources, but source ownership is not independently verified; candidates should check the visible links.
Grounding supports attribution, not a guarantee that every source claim is correct or current.

`CompanyBrief` contains status, dated facts, source IDs/links, a note and Google's Search Suggestions.
The browser shows inline source links and Suggestions in a script-free, opaque-origin iframe. Never
render that HTML with unsandboxed `dangerouslySetInnerHTML`. Search Suggestions are presentation data
and are excluded from agent payloads. Source and fact counts and sizes are bounded in schemas.py.

## Persistence and failure handling

`company_research` caches by normalized company, role and URL **within workspace and candidate scope**.
Successful research is retained and reused until **Refresh research** explicitly requests an update.
Its research date stays visible; saved does not mean freshly verified. Failed calls have a 60-second
negative cache. A failed refresh retains the last good result for future reuse. Cached IDs require
ownership and matching company/role/URL. Changing inputs resolves a different entry. The interview
copies the complete brief into `_brief`, preserving its sources even after later refreshes. The legacy
`expires_at` column is used only for failure backoff; successful rows from before this change are reusable.
Cache hits occur before paid quota reservation and make no model/search call. Concurrent first-ever cache
misses are not coalesced and can make separate calls; completed results remain reusable.

Search outages or missing credentials do not block a general role practice session. The UI says
research is unavailable and the supplied JD guides the agents. Quota reservations are required before
search. An account quota error remains an account error. Company source availability is not a health
probe and no paid search happens at application startup. Explicit test mode disables live search.

The company brief informs planning and follow-ups. Evaluators still score the actual question and
answer using the same rubric, with no employer prestige weighting or prediction of private hiring
standards. Generated JDs remain suggested practice briefs, not verified vacancies.

## Configuration and verification

Set `GEMINI_API_KEY` and `COMPANY_RESEARCH_ENABLED=true` in backend/.env. Assign
`company_research = "gemini_search"` in models.toml. The old COMPANY_RESEARCH_MODEL variable is retired.
Restart the API and worker. Google OAuth credentials are separate and do not authorize search.
The configured Google AI project must have access and quota for the selected model and search tool.
See RUN.md for the explicit paid smoke command and fixture-only tests.

Official implementation reference: [Google Search grounding](https://ai.google.dev/gemini-api/docs/generate-content/google-search).

## Saved job descriptions

`setup_artifacts` stores generated descriptions and title suggestions privately per candidate/account.
JD reuse matches normalized role, company, experience and company URL. Matching Generate requests return
saved content without paid inference. **Regenerate** creates a new saved revision; the selector offers
up to 50 recent descriptions, and loading one restores its input fields and research snapshot. Edits in
the textarea remain the user's draft and enter the interview when started; they do not overwrite the
original generated artifact. Changing inputs creates a different cache key. A research refresh does not
overwrite an earlier JD; explicitly regenerate to use the updated context. Previously generated drafts
that were never stored cannot be recovered; older interview descriptions remain in their interviews.

Endpoints: `GET /api/setup/job-descriptions`, `GET /api/setup/job-descriptions/{id}`,
`POST /api/suggest/job-description` and `POST /api/company-research` (`force_refresh: true` for paid refresh).
Successful outputs are saved before responding. Retrieval remains available after monthly AI allowance
exhaustion. Cache content is not shared between accounts or candidates.
