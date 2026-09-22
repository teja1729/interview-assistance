# Provider adapters

Start with docs/ADDING_A_PROVIDER.md. Implement `generate` and return `Completion`; do not query
application tables or catch an exception just to leak its body to clients. Credentials are resolved
from environment references in the operator's TOML. Availability is configuration presence, not
a paid health probe. The `[agents]` section assigns a profile to each role. Browser users cannot
configure profiles, URLs or API keys. Interview creation snapshots resolved model settings and
credential environment references. Apply `profile.timeout_seconds` as a cancellable total deadline
and `profile.max_output_tokens` as an output limit; leave retries to the runtime. Every adapter
uses a local async scope so cancellation releases its HTTP resources.

Declare verified context_tokens, capabilities and optional concurrency/tokenizer settings per profile.
Search-capable providers implement search and return a sourced CompanyBrief; the same runtime owns
budgets, retries and diagnostics. Do not silently downgrade search to ungrounded text.
Sarvam wire schemas omit regex patterns after synthetic live tests exposed malformed quoted strings
from its constrained decoder. Full Pydantic/semantic validation still applies locally. Never repair
candidate evidence by altering generated quotes or by silently inventing missing contract fields.
