from pydantic import ValidationError

from backend.agent.contracts.planning import PlanningBrief
from backend.agent.intent_extraction import build_initial_planning_brief as build_minimal_planning_brief
from backend.agent.providers.errors import LlmProviderError


class PlanningBriefBuilder:
    """Build PlanningBrief from user language using the LLM, with a non-inferential fallback."""

    def __init__(self, provider=None) -> None:
        self.provider = provider

    def build_initial_planning_brief(self, user_message: str) -> PlanningBrief:
        if self.provider and hasattr(self.provider, "generate_planning_brief"):
            try:
                payload = self.provider.generate_planning_brief(
                    system_prompt=planning_brief_system_prompt(),
                    user_prompt=user_message,
                )
                payload = {
                    "mode": "initial_plan",
                    "origin_message": user_message,
                    **payload,
                }
                payload["builder_source"] = "llm"
                payload["builder_fallback_reason"] = None
                return PlanningBrief.model_validate(payload)
            except LlmProviderError as error:
                return build_minimal_planning_brief(user_message, fallback_reason=error.code)
            except (ValidationError, TypeError, ValueError) as error:
                return build_minimal_planning_brief(user_message, fallback_reason=type(error).__name__)
        return build_minimal_planning_brief(user_message, fallback_reason="provider_unavailable")


def planning_brief_system_prompt() -> str:
    return (
        "You extract a structured PlanningBrief for a travel planning agent. "
        "Return JSON only. Do not invent unknown details. "
        "Use null or [] when the user did not provide enough information. "
        "Fields: mode, origin_message, traveler_count, date_range, duration_days, budget, pace, "
        "destination_candidates, interests, dislikes, hard_constraints, soft_preferences, "
        "affected_day_ids, affected_node_ids. "
        "Set mode to initial_plan. Use concise normalized Chinese labels when the user writes Chinese."
    )
