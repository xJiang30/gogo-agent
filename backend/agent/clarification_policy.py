import json

from pydantic import ValidationError

from backend.agent.contracts.clarification import ClarificationDecision, ClarificationQuestion
from backend.agent.providers.errors import LlmProviderError


class ClarificationPolicy:
    """Decide whether a user turn needs questions before planning starts."""

    def __init__(self, provider=None) -> None:
        self.provider = provider

    def decide(self, *, user_message: str, trip: dict | None, intent: dict) -> ClarificationDecision:
        kind = intent.get("kind")
        if trip or kind != "initial_plan":
            return ClarificationDecision(should_ask=False)

        if self.provider and hasattr(self.provider, "generate_clarification_decision"):
            try:
                payload = self.provider.generate_clarification_decision(
                    system_prompt=clarification_system_prompt(),
                    user_prompt=clarification_user_prompt(user_message=user_message, intent=intent),
                )
                return ClarificationDecision.model_validate(payload)
            except (LlmProviderError, ValidationError, TypeError, ValueError) as error:
                return fallback_clarification_decision(reason=f"clarification_fallback:{type(error).__name__}")

        return fallback_clarification_decision(reason="clarification_fallback:provider_unavailable")


def fallback_clarification_decision(*, reason: str) -> ClarificationDecision:
    return ClarificationDecision(
        should_ask=True,
        questions=[
            ClarificationQuestion(
                id="destination",
                text="你想去哪个城市、国家或区域？",
                required=True,
            ),
            ClarificationQuestion(
                id="duration_days",
                text="大概玩几天？",
                required=True,
            ),
        ],
        reason=reason,
    )


def clarification_system_prompt() -> str:
    return (
        "You decide whether a travel planning request needs clarification before planning. "
        "Return only JSON that matches this schema: "
        "{should_ask: boolean, questions: [{id: string, text: string, required: boolean, answer_type: string}], reason: string}. "
        "Ask only for information that is required to start a useful initial plan. "
        "If the user provided enough information to start, return should_ask=false and questions=[]."
    )


def clarification_user_prompt(*, user_message: str, intent: dict) -> str:
    return json.dumps(
        {
            "user_message": user_message,
            "intent": intent,
            "minimum_required_for_initial_plan": ["destination", "duration_or_date_range"],
            "question_guidelines": [
                "Use the user's language when possible.",
                "Ask concise questions.",
                "Prefer one question per missing required field.",
            ],
        },
        ensure_ascii=False,
    )
