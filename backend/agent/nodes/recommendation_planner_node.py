import json

from pydantic import ValidationError

from backend.agent.contracts.graph_state import TripPlanningGraphState
from backend.agent.contracts.errors import GraphErrorEnvelope
from backend.agent.contracts.recommendation_output import TravelPlanRecommendation
from backend.agent.providers.errors import LlmProviderError


def recommendation_planner_node(state: TripPlanningGraphState, provider) -> TripPlanningGraphState:
    """Generate complete recommendation candidates from normalized API/research context."""
    if state.mode != "initial_plan":
        state.trace.append({"node": "recommendation_planner_node", "status": "skipped", "reason": "not_initial_plan"})
        return state
    if not hasattr(provider, "generate_recommendations"):
        state.graph_error = GraphErrorEnvelope(
            decision="retry_later",
            retryable=False,
            error_code="provider_capability_error",
            failed_domains=["recommendation_planner"],
            message="Recommendation planner requires a provider with generate_recommendations.",
        )
        state.trace.append({"node": "recommendation_planner_node", "status": "error", "error_code": "provider_capability_error"})
        return state

    try:
        payload = provider.generate_recommendations(
            system_prompt=recommendation_planner_system_prompt(),
            user_prompt=recommendation_planner_user_prompt(state),
        )
        recommendations = parse_recommendations(payload)
    except LlmProviderError as error:
        state.graph_error = GraphErrorEnvelope(
            decision="retry_later",
            retryable=error.retryable,
            error_code=error.code,
            failed_domains=["recommendation_planner"],
            message=str(error),
        )
        state.trace.append(
            {
                "node": "recommendation_planner_node",
                "status": "error",
                "error_code": error.code,
                "retryable": error.retryable,
            },
        )
        return state
    except (ValidationError, TypeError, ValueError) as error:
        state.graph_error = GraphErrorEnvelope(
            decision="fail_run",
            retryable=False,
            error_code=type(error).__name__,
            failed_domains=["recommendation_planner"],
            message="Recommendation planner returned invalid recommendations.",
        )
        state.trace.append(
            {
                "node": "recommendation_planner_node",
                "status": "error",
                "error_code": type(error).__name__,
                "retryable": False,
            },
        )
        return state

    state.recommendations = recommendations[:3]
    state.trace.append({"node": "recommendation_planner_node", "status": "success", "recommendations": len(state.recommendations)})
    return state


def parse_recommendations(payload: dict) -> list[TravelPlanRecommendation]:
    raw_items = payload.get("recommendations", [])
    raw_items = [normalize_recommendation_payload(item) for item in raw_items]
    recommendations = [TravelPlanRecommendation.model_validate(item) for item in raw_items]
    if len(recommendations) < 3:
        raise ValueError("recommendation_planner_requires_three_recommendations")
    return recommendations


def normalize_recommendation_payload(item: dict) -> dict:
    normalized = dict(item)
    field_aliases = {
        "bestFor": "best_for",
        "stayPlan": "stay_plan",
        "dayPlans": "day_plans",
        "mobilityPlan": "mobility_plan",
        "foodPlan": "food_plan",
        "missingInfo": "missing_info",
    }
    for source, target in field_aliases.items():
        if source in normalized:
            normalized[target] = normalized.pop(source)
    if isinstance(normalized.get("stay_plan"), dict):
        normalize_in_place(normalized["stay_plan"], {"anchorArea": "anchor_area", "hotelSwitches": "hotel_switches"})
    if isinstance(normalized.get("mobility_plan"), dict) and isinstance(normalized["mobility_plan"].get("dayTrip"), dict):
        normalized["mobility_plan"]["day_trip"] = normalized["mobility_plan"].pop("dayTrip")
    if isinstance(normalized.get("mobility_plan"), dict) and isinstance(normalized["mobility_plan"].get("day_trip"), dict):
        normalize_in_place(
            normalized["mobility_plan"]["day_trip"],
            {"estimatedOneWayTime": "estimated_one_way_time", "transferPressure": "transfer_pressure"},
        )
    if isinstance(normalized.get("food_plan"), dict):
        normalize_in_place(
            normalized["food_plan"],
            {"mustTry": "must_try", "suggestedAreas": "suggested_areas", "reservationNotes": "reservation_notes"},
        )
    if isinstance(normalized.get("day_plans"), list):
        for day in normalized["day_plans"]:
            if isinstance(day, dict) and isinstance(day.get("blocks"), list):
                for block in day["blocks"]:
                    if isinstance(block, dict):
                        normalize_in_place(block, {"timeOfDay": "time_of_day"})
    return normalized


def normalize_in_place(payload: dict, aliases: dict[str, str]) -> None:
    for source, target in aliases.items():
        if source in payload:
            payload[target] = payload.pop(source)


def recommendation_planner_system_prompt() -> str:
    return (
        "You are the main travel recommendation planner. Return JSON only. "
        "Generate exactly 3 complete TravelPlanRecommendation objects. "
        "Use the candidateContext from stay, mobility, and experience specialists. "
        "Do not return placeholders. Do not invent unavailable booking facts. "
        "Each recommendation must include stay_plan, mobility_plan, food_plan, day_plans, evidence, warnings, and score."
    )


def recommendation_planner_user_prompt(state: TripPlanningGraphState) -> str:
    payload = {
        "planningBrief": state.planning_brief.model_dump(),
        "skeletonPlan": state.skeleton_plan,
        "candidateContext": state.candidate_context or {},
    }
    return json.dumps(payload, ensure_ascii=False)
