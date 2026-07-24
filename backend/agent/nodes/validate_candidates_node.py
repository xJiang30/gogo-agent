from backend.agent.contracts.graph_state import TripPlanningGraphState
from backend.agent.contracts.errors import GraphErrorEnvelope
from backend.agent.contracts.validation import CandidateValidationResult, ValidationResult


def validate_candidates_node(state: TripPlanningGraphState) -> TripPlanningGraphState:
    """Validate candidate quality before final output."""
    valid_recommendations = []
    validation_results = []

    for recommendation in state.recommendations:
        reasons = validation_reasons(recommendation)
        status = "fail" if reasons else "pass"
        validation_results.append(
            {
                "candidate_id": recommendation.id,
                "status": status,
                "reasons": reasons,
            },
        )
        if status == "pass":
            valid_recommendations.append(recommendation)

    state.validation_result = ValidationResult(
        candidate_results=[
            CandidateValidationResult(
                candidate_id=item["candidate_id"],
                status=item["status"],
                reasons=item["reasons"],
            )
            for item in validation_results
        ],
        overall_status="pass" if valid_recommendations else "fail",
    )
    if not valid_recommendations:
        state.graph_error = GraphErrorEnvelope(
            decision="fail_run",
            retryable=False,
            error_code="candidate_validation_failed",
            failed_domains=["validate_candidates"],
            message="All recommendation candidates failed validation.",
        )
    else:
        state.recommendations = valid_recommendations
    state.trace.append(
        {
            "node": "validate_candidates_node",
            "status": state.validation_result.overall_status,
            "candidate_results": validation_results,
        },
    )
    return state


def validation_reasons(recommendation) -> list[str]:
    reasons = []
    if not recommendation.day_plans:
        reasons.append("missing_day_plans")
    if not recommendation.food_plan.must_try:
        reasons.append("missing_food_plan")
    if not recommendation.mobility_plan.day_trip.destination:
        reasons.append("missing_day_trip_destination")
    if not recommendation.evidence:
        reasons.append("missing_evidence")
    if (recommendation.score or 0) < 1.2:
        reasons.append("low_score")

    for day in recommendation.day_plans:
        for block in day.blocks:
            if block.type == "meal" and looks_like_non_food(block.title):
                reasons.append("meal_block_looks_like_day_trip")
    return reasons


def looks_like_non_food(title: str) -> bool:
    lowered = title.lower()
    return any(token in lowered for token in ["day trip", "一日游", "周边游"])
