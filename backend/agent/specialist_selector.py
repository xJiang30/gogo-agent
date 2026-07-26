import json

from pydantic import ValidationError

from backend.agent.contracts.replan_routing import ReplanNeed, SpecialistSelection
from backend.agent.providers.errors import LlmProviderError


class SpecialistSelector:
    """Select specialist domains/API-backed checks needed for a user turn."""

    def __init__(self, provider=None) -> None:
        self.provider = provider

    def select(self, *, user_message: str, intent: dict) -> SpecialistSelection:
        if self.provider and hasattr(self.provider, "generate_specialist_selection"):
            try:
                payload = self.provider.generate_specialist_selection(
                    system_prompt=specialist_selector_system_prompt(),
                    user_prompt=specialist_selector_user_prompt(user_message=user_message, intent=intent),
                )
                return SpecialistSelection.model_validate(payload)
            except (LlmProviderError, ValidationError, TypeError, ValueError):
                pass
        return fallback_specialist_selection(user_message=user_message, intent=intent)


def fallback_specialist_selection(*, user_message: str, intent: dict) -> SpecialistSelection:
    text = f"{user_message} {intent}".lower()
    needs: list[ReplanNeed] = []
    reasons: list[str] = []

    add_if_mentions(needs, reasons, text, ReplanNeed.WEATHER, ["天气", "下雨", "雨", "台风", "weather"], "Weather may affect pacing or outdoor choices")
    add_if_mentions(needs, reasons, text, ReplanNeed.TICKET, ["门票", "预约", "买票", "票", "ticket"], "Ticket or reservation availability may affect feasibility")
    add_if_mentions(needs, reasons, text, ReplanNeed.PRICE, ["价格", "票价", "预算", "贵", "便宜", "price"], "Price may affect the recommendation")
    add_if_mentions(needs, reasons, text, ReplanNeed.FLIGHT, ["机票", "航班", "飞机", "flight"], "Flight timing or price may affect mobility")
    add_if_mentions(needs, reasons, text, ReplanNeed.RAIL, ["高铁", "火车", "新干线", "rail", "train"], "Rail timing may affect mobility")
    add_if_mentions(needs, reasons, text, ReplanNeed.STAY, ["住宿", "酒店", "民宿", "hotel"], "Stay constraints may affect the plan")
    add_if_mentions(needs, reasons, text, ReplanNeed.MOBILITY, ["交通", "路线", "打车", "地铁", "公交", "换乘", "taxi", "route", "transport", "subway", "bus"], "Mobility constraints may affect the plan")
    add_if_mentions(needs, reasons, text, ReplanNeed.EXPERIENCE, ["景点", "餐厅", "美食", "体验", "吃", "restaurant", "food", "attraction", "experience"], "Experience quality may affect the plan")

    return SpecialistSelection(optional=needs, reasons=reasons)


def add_if_mentions(
    needs: list[ReplanNeed],
    reasons: list[str],
    text: str,
    need: ReplanNeed,
    keywords: list[str],
    reason: str,
) -> None:
    if need in needs:
        return
    if any(keyword in text for keyword in keywords):
        needs.append(need)
        reasons.append(reason)


def specialist_selector_system_prompt() -> str:
    return (
        "You select travel specialist capabilities needed for the user's turn. Return JSON only matching "
        "SpecialistSelection: {optional: string[], reasons: string[], execution_mode: string}. "
        "Allowed needs: stay, mobility, experience, weather, ticket, flight, rail, price. "
        "Return optional capabilities from the user message only; required node/tag capabilities are added by TravelAdvisor. "
        "Use execution_mode lightweight unless the caller explicitly asks for graph-level replan."
    )


def specialist_selector_user_prompt(*, user_message: str, intent: dict) -> str:
    return json.dumps(
        {
            "user_message": user_message,
            "intent": intent,
        },
        ensure_ascii=False,
    )
