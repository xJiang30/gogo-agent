from backend.agent.contracts.planning import PlanningBrief


def build_initial_planning_brief(user_message: str, *, fallback_reason: str | None = None) -> PlanningBrief:
    """Schema-safe fallback only; do not infer intent fields with fixed rules."""
    return PlanningBrief(
        mode="initial_plan",
        origin_message=user_message,
        builder_source="fallback",
        builder_fallback_reason=fallback_reason,
    )
