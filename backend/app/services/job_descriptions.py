"""Generate a structured role brief and render an editable, explicitly attributed draft."""

from ..agents.runtime import execute
from ..providers.base import agent_profiles, profiles
from ..schemas import JobDescriptionDraft
from . import setup_cache
from .company_research import research
from .usage import consume, rate_limit


def generate(session, ctx, payload):
    inputs = setup_cache.inputs_for(payload)
    if not payload.get("force_refresh") and (saved := setup_cache.lookup(session, ctx, "job_description", inputs)):
        return setup_cache.public(saved)
    rate_limit(session, ctx.workspace)
    consume(session, ctx.workspace)
    routing = agent_profiles()
    _, company = research(
        session,
        ctx,
        payload.get("company", ""),
        payload["job_title"],
        payload.get("company_url", ""),
        payload.get("company_research_id"),
    )
    context = company.model_dump(exclude={"search_suggestions"})
    draft = execute(
        "assistant",
        {**inputs, "company_context": context},
        JobDescriptionDraft,
        workspace_id=ctx.workspace.id,
        user_id=ctx.user.id,
        ai_profiles=routing,
        engine=session.bind,
    )
    selected = profiles().get(routing["assistant"])
    demo = bool(selected and selected.provider == "demo")
    sections = [
        payload["job_title"],
        "Role overview\n" + draft.role_summary,
    ]
    for title, items in (
        ("Responsibilities", draft.responsibilities),
        ("Requirements", draft.requirements),
        ("Nice to have", draft.preferred),
        ("First 90 days", draft.early_outcomes),
    ):
        sections.append(title + "\n" + "\n".join(f"- {item}" for item in items))
    if demo:
        sections.insert(0, "DEMO SAMPLE — synthetic content from the explicitly enabled local test mode.")
    return setup_cache.save(
        session,
        ctx,
        "job_description",
        inputs,
        {"job_description": "\n\n".join(sections), "demo": demo, "company_context": company.model_dump()},
    )
