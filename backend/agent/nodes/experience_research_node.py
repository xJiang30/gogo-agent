import json

from backend.agent.contracts.graph_state import TripPlanningGraphState
from backend.agent.contracts.research import ResearchResult
from .run_research_step import run_research_step


def experience_research_node(state: TripPlanningGraphState, provider) -> TripPlanningGraphState:
    result = run_research_step(
        domain="experience",
        research_call=lambda: build_experience_result(state, provider),
    )
    state.experience_outcome = result["outcome"]
    state.graph_error = result["graph_error"]
    if state.experience_outcome.result:
        state.experience_result = state.experience_outcome.result
    state.trace.append({"node": "experience_research_node", "status": state.experience_outcome.status})
    return state


def build_experience_result(state: TripPlanningGraphState, provider) -> ResearchResult:
    api_context = build_experience_api_context(state, provider)
    payload = provider.generate_research(
        domain="experience",
        system_prompt="You are the experience specialist for a trip-planning agent. Return only JSON.",
        user_prompt="\n".join(
            [
                "Analyze food, city activities, energy pacing, and day feel.",
                "Return only JSON with fields: summary, options, warnings, missingInfo, evidence, assumptions, confidence.",
                "Each option should include: id, title, foodHighlights, cityExperiences, rationale.",
                "foodHighlights must be dishes, restaurants, food areas, or snacks, never a day-trip title.",
                "Keep summary under 2 sentences. Do not include fabricated source names.",
                f"Weather API context: {json.dumps(api_context.get('weather'), ensure_ascii=False)}",
                f"Planning brief: {state.planning_brief.model_dump_json()}",
                f"Skeleton plan: {json.dumps(state.skeleton_plan, ensure_ascii=False)}",
            ],
        ),
    )
    return ResearchResult(
        domain="experience",
        summary=payload.get("summary", ""),
        options=payload.get("options", []),
        warnings=payload.get("warnings", []),
        missing_info=payload.get("missingInfo", payload.get("missing_info", [])),
        evidence=payload.get("evidence", []),
        assumptions=payload.get("assumptions", []),
        confidence=payload.get("confidence"),
        raw={**payload, "api_context": api_context},
    )


def build_experience_api_context(state: TripPlanningGraphState, provider) -> dict:
    context = {"weather": None}
    if hasattr(provider, "get_weather_context"):
        try:
            context["weather"] = provider.get_weather_context(planning_brief=state.planning_brief)
        except Exception as error:
            context["weather"] = {
                "source": "weather_api",
                "warnings": [f"Weather API unavailable: {type(error).__name__}"],
            }
    return context
