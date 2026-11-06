# Company research

New company web research is currently unavailable because the application has no search provider.
When a candidate starts an interview, the supplied job description remains the source of role context.
The UI reports research as unavailable rather than inventing company facts.

Previously saved, candidate-owned research snapshots remain readable and may be reused. Cached IDs
are still checked against account ownership and the company, role and URL. An interview copies any
reused brief into its private snapshot so later changes to the cache do not alter that interview.
A forced refresh reports unavailable and does not replace a previously successful cached result.

The `CompanyBrief` and API contracts remain for stored data compatibility. No live web search or
provider call occurs on a cache miss, and unavailable results do not consume model quota.
