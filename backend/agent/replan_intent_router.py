import json

from pydantic import ValidationError

from backend.agent.contracts.replan_routing import ReplanRoutingDecision, ReplanScope
from backend.agent.contracts.routing_and_proposal import EscalationDecision
from backend.agent.providers.errors import LlmProviderError


class ReplanIntentRouter:
    """Classify the user's turn into a product-level planning scope."""

    def __init__(self, provider=None) -> None:
        self.provider = provider

    def classify(self, *, user_message: str, trip: dict | None, intent: dict) -> ReplanRoutingDecision:
        if self.provider and hasattr(self.provider, "generate_replan_routing_decision"):
            try:
                payload = self.provider.generate_replan_routing_decision(
                    system_prompt=replan_router_system_prompt(),
                    user_prompt=replan_router_user_prompt(user_message=user_message, trip=trip, intent=intent),
                )
                return ReplanRoutingDecision.model_validate(payload)
            except (LlmProviderError, ValidationError, TypeError, ValueError):
                pass
        return fallback_replan_routing_decision(user_message=user_message, trip=trip, intent=intent)


def fallback_replan_routing_decision(*, user_message: str, trip: dict | None, intent: dict) -> ReplanRoutingDecision:
    kind = normalize_intent_kind(intent.get("kind"))
    affected_day_ids = list(intent.get("affected_day_ids", []))
    affected_node_ids = get_affected_node_ids(intent)
    requested_mode = intent.get("mode") or intent.get("action")

    if kind == "initial_plan" or requested_mode == "initial_plan":
        return ReplanRoutingDecision(
            scope=ReplanScope.INITIAL_PLAN,
            decision=EscalationDecision.GRAPH_REPLAN.value,
            output_kind="recommendation_set",
            affected_day_ids=affected_day_ids,
            affected_node_ids=affected_node_ids,
            reasons=["Initial planning requires graph orchestration"],
        )

    if kind == "regenerate_recommendations" or requested_mode == "regenerate_recommendations":
        return ReplanRoutingDecision(
            scope=ReplanScope.REGENERATE_RECOMMENDATIONS,
            decision=EscalationDecision.REGENERATE_RECOMMENDATIONS.value,
            output_kind="recommendation_set",
            affected_day_ids=affected_day_ids,
            affected_node_ids=affected_node_ids,
            reasons=["User requested a new recommendation set before committing to a trip"],
        )

    if kind == "replace":
        return ReplanRoutingDecision(
            scope=ReplanScope.LIGHTWEIGHT_RESEARCH,
            decision=EscalationDecision.LIGHTWEIGHT_RESEARCH.value,
            output_kind="answer",
            affected_day_ids=affected_day_ids,
            affected_node_ids=affected_node_ids,
            reasons=["Single-node free text is consultative unless the user triggers explicit replan"],
        )

    if kind == "research":
        return ReplanRoutingDecision(
            scope=ReplanScope.LIGHTWEIGHT_RESEARCH,
            decision=EscalationDecision.LIGHTWEIGHT_RESEARCH.value,
            output_kind="answer",
            affected_day_ids=affected_day_ids,
            affected_node_ids=affected_node_ids,
            reasons=["Needs lightweight provider lookup, not trip mutation"],
        )

    if kind == "replan":
        if not trip:
            return ReplanRoutingDecision(
                scope=ReplanScope.REGENERATE_RECOMMENDATIONS,
                decision=EscalationDecision.REGENERATE_RECOMMENDATIONS.value,
                output_kind="recommendation_set",
                affected_day_ids=affected_day_ids,
                affected_node_ids=affected_node_ids,
                reasons=["No committed trip exists, so replan means regenerating recommendations"],
            )

        if len(affected_day_ids) >= 2:
            scope = ReplanScope.CROSS_DAY_REPLAN
            reason = "Touches multiple committed trip days"
        else:
            scope = ReplanScope.DAY_REPLAN
            reason = "Touches one committed trip day"
        return ReplanRoutingDecision(
            scope=scope,
            decision=EscalationDecision.GRAPH_REPLAN.value,
            output_kind="proposal",
            affected_day_ids=affected_day_ids,
            affected_node_ids=affected_node_ids,
            reasons=[reason],
        )

    return ReplanRoutingDecision(
        scope=ReplanScope.DISCUSSION_TURN,
        decision=EscalationDecision.DIRECT_ANSWER.value,
        output_kind="answer",
        affected_day_ids=affected_day_ids,
        affected_node_ids=affected_node_ids,
        reasons=["Can answer directly without changing the trip"],
    )


def normalize_intent_kind(kind: str | None) -> str:
    if kind in {"replace_hotel", "replace_node", "replace_transport"}:
        return "replace"
    if kind in {"day_replan", "cross_day_replan", "full_replan", "all_replan"}:
        return "replan"
    if kind in {"initial_plan", "replace", "research", "replan", "regenerate_recommendations"}:
        return kind
    return "ask"


def get_affected_node_ids(intent: dict) -> list[str]:
    if intent.get("affected_node_ids"):
        return intent["affected_node_ids"]
    if intent.get("node_id"):
        return [intent["node_id"]]
    return []


def replan_router_system_prompt() -> str:
    return (
        "You classify a travel advisor user turn. Return JSON only matching ReplanRoutingDecision: "
        "{scope, decision, output_kind, affected_day_ids, affected_node_ids, reasons}. "
        "Use scope values: initial_plan, discussion_turn, local_node_proposal, day_replan, "
        "cross_day_replan, regenerate_recommendations, lightweight_research. "
        "Use decision values: direct_answer, lightweight_research, local_proposal, graph_replan, regenerate_recommendations. "
        "Important product rule: after a Trip Board exists, free-text ask/replace/check/compare turns are consultative "
        "and should use lightweight_research or direct_answer. Only explicit day, cross-day, or full-trip replan/edit "
        "actions should use graph_replan and output a proposal. Do not choose local_proposal for normal free text. "
        "If the user has not committed to a trip and asks for a different set of plans, choose regenerate_recommendations."
    )


def replan_router_user_prompt(*, user_message: str, trip: dict | None, intent: dict) -> str:
    return json.dumps(
        {
            "user_message": user_message,
            "has_current_trip": bool(trip),
            "intent": intent,
        },
        ensure_ascii=False,
    )
