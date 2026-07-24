import json

from backend.agent.contracts.graph_state import TripPlanningGraphState
from backend.agent.contracts.research import ResearchResult
from .run_research_step import run_research_step


def mobility_research_node(state: TripPlanningGraphState, provider) -> TripPlanningGraphState:
    result = run_research_step(
        domain="mobility",
        research_call=lambda: build_mobility_result(state, provider),
    )
    state.mobility_outcome = result["outcome"]
    state.graph_error = result["graph_error"]
    if state.mobility_outcome.result:
        state.mobility_result = state.mobility_outcome.result
    state.trace.append({"node": "mobility_research_node", "status": state.mobility_outcome.status})
    return state


def build_mobility_result(state: TripPlanningGraphState, provider) -> ResearchResult:
    api_context = build_mobility_api_context(state, provider)
    payload = provider.generate_research(
        domain="mobility",
        system_prompt="You are the mobility specialist for a trip-planning agent. Return only JSON.",
        user_prompt="\n".join(
            [
                "Analyze one nearby day trip, transport, transfer pressure, and cross-day risk.",
                "Return only JSON with fields: summary, options, warnings, missingInfo, evidence, assumptions, confidence.",
                "Each option should include: id, title, destination, transport, estimatedOneWayTime, transferPressure, rationale.",
                "Keep summary under 2 sentences. Do not include fabricated source names.",
                f"Mobility API context: {json.dumps(api_context.get('mobility'), ensure_ascii=False)}",
                f"Planning brief: {state.planning_brief.model_dump_json()}",
                f"Skeleton plan: {json.dumps(state.skeleton_plan, ensure_ascii=False)}",
            ],
        ),
    )
    return ResearchResult(
        domain="mobility",
        summary=payload.get("summary", ""),
        options=payload.get("options", []),
        warnings=payload.get("warnings", []),
        missing_info=payload.get("missingInfo", payload.get("missing_info", [])),
        evidence=payload.get("evidence", []),
        assumptions=payload.get("assumptions", []),
        confidence=payload.get("confidence"),
        raw={**payload, "api_context": api_context},
    )


def build_mobility_api_context(state: TripPlanningGraphState, provider) -> dict:
    context = {"mobility": None}
    if hasattr(provider, "get_mobility_context"):
        try:
            context["mobility"] = provider.get_mobility_context(planning_brief=state.planning_brief)
        except Exception as error:
            context["mobility"] = {
                "source": "mobility_api",
                "warnings": [f"Mobility API unavailable: {type(error).__name__}"],
            }
    return context
