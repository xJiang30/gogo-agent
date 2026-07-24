import json

from backend.agent.contracts.graph_state import TripPlanningGraphState
from backend.agent.contracts.research import ResearchResult
from .run_research_step import run_research_step


def stay_research_node(state: TripPlanningGraphState, provider) -> TripPlanningGraphState:
    result = run_research_step(
        domain="stay",
        research_call=lambda: build_stay_result(state, provider),
    )
    state.stay_outcome = result["outcome"]
    state.graph_error = result["graph_error"]
    if state.stay_outcome.result:
        state.stay_result = state.stay_outcome.result
    state.trace.append({"node": "stay_research_node", "status": state.stay_outcome.status})
    return state


def build_stay_result(state: TripPlanningGraphState, provider) -> ResearchResult:
    api_context = build_stay_api_context(state, provider)
    payload = provider.generate_research(
        domain="stay",
        system_prompt="You are the stay specialist for a trip-planning agent. Return only JSON.",
        user_prompt="\n".join(
            [
                "Analyze lodging strategy for a frontend travel-plan card.",
                "Return only JSON with fields: summary, options, warnings, missingInfo, evidence, assumptions, confidence.",
                "Each option should include: id, title, anchorArea, rationale.",
                "Keep summary under 2 sentences. Do not include fabricated source names.",
                f"Stay API context: {json.dumps(api_context.get('stay'), ensure_ascii=False)}",
                f"Planning brief: {state.planning_brief.model_dump_json()}",
                f"Skeleton plan: {json.dumps(state.skeleton_plan, ensure_ascii=False)}",
            ],
        ),
    )
    return ResearchResult(
        domain="stay",
        summary=payload.get("summary", ""),
        options=payload.get("options", []),
        warnings=payload.get("warnings", []),
        missing_info=payload.get("missingInfo", payload.get("missing_info", [])),
        evidence=payload.get("evidence", []),
        assumptions=payload.get("assumptions", []),
        confidence=payload.get("confidence"),
        raw={**payload, "api_context": api_context},
    )


def build_stay_api_context(state: TripPlanningGraphState, provider) -> dict:
    context = {"stay": None}
    if hasattr(provider, "get_stay_context"):
        try:
            context["stay"] = provider.get_stay_context(planning_brief=state.planning_brief)
        except Exception as error:
            context["stay"] = {
                "source": "stay_api",
                "warnings": [f"Stay API unavailable: {type(error).__name__}"],
            }
    return context
