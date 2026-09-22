"""Normalize search metadata into sourced facts; no database or service dependencies."""

import time
from urllib.parse import urlsplit

from ..schemas import CompanyBrief, CompanyFact, Source, public_company_url


def unavailable(company, note):
    return CompanyBrief(company=company, status="unavailable", note=note)


def parse_grounding(company, response, company_url=""):
    candidate = response.candidates[0] if response.candidates else None
    metadata = candidate.grounding_metadata if candidate else None
    if not metadata or not metadata.web_search_queries:
        return unavailable(
            company,
            "Company information could not be verified with web search. Your job description will guide the interview.",
        )
    sources, by_index = [], {}
    for index, chunk in enumerate(metadata.grounding_chunks or []):
        web = chunk.web
        if not web or not web.uri or len(sources) >= 8:
            continue
        try:
            public_company_url(web.uri)
        except ValueError:
            continue
        parsed = urlsplit(web.uri)
        if company_url:
            official = (urlsplit(company_url).hostname or "").removeprefix("www.")
            # Search redirect URIs are opaque; Google's source title is often the origin domain.
            candidates = [(parsed.hostname or "").removeprefix("www."), (web.title or "").lower().removeprefix("www.")]
            if not any(host == official or host.endswith("." + official) for host in candidates):
                continue
        source = Source(id=f"s{index}", title=(web.title or parsed.hostname)[:300], url=web.uri)
        sources.append(source)
        by_index[index] = source.id
    facts = []
    for support in metadata.grounding_supports or []:
        text = support.segment.text if support.segment else ""
        ids = [by_index[i] for i in support.grounding_chunk_indices or [] if i in by_index]
        if text and ids and len(text) <= 1200 and len(facts) < 8:
            facts.append(CompanyFact(text=text, source_ids=list(dict.fromkeys(ids))))
    if not facts:
        return unavailable(
            company,
            "Search did not return sufficiently sourced company details. Add an official company or job URL to narrow the search.",
        )
    # The model must not silently pick one of several similarly named organizations.
    if "ambiguous" in (response.text or "").lower():
        return unavailable(
            company, "Several companies match this name. Add the official company or job URL, then research again."
        )
    suggestions = metadata.search_entry_point.rendered_content if metadata.search_entry_point else ""
    return CompanyBrief(
        company=company,
        status="researched",
        facts=facts,
        sources=sources,
        researched_at=time.time(),
        search_suggestions=(suggestions or "")[:50000],
        note="Web-sourced preparation context. Check that the sources refer to your target company.",
    )
