import json

from backend.agent.providers.errors import LlmProviderError


class LightweightFlows:
    def __init__(self, provider=None) -> None:
        self.provider = provider
        self.metrics = {
            "direct_answer_count": 0,
            "lightweight_research_count": 0,
        }

    def answer(self, request: dict) -> dict:
        self.metrics["direct_answer_count"] += 1
        if self.provider and hasattr(self.provider, "generate_answer"):
            text = self.provider.generate_answer(
                system_prompt="You are a concise travel advisor. Answer directly without changing the trip.",
                user_prompt=request.get("user_message", ""),
            )
            return {
                "kind": "answer",
                "text": text,
            }
        raise LlmProviderError(
            code="provider_capability_error",
            message="Lightweight answer requires a provider with generate_answer",
            retryable=False,
        )

    def research(self, request: dict) -> dict:
        self.metrics["lightweight_research_count"] += 1
        if self.provider and hasattr(self.provider, "generate_answer"):
            text = self.provider.generate_answer(
                system_prompt=contextual_research_system_prompt(),
                user_prompt=contextual_research_user_prompt(request),
            )
            return {
                "kind": "answer",
                "text": text,
            }
        raise LlmProviderError(
            code="provider_capability_error",
            message="Lightweight research requires a provider with generate_answer",
            retryable=False,
        )

    def get_metrics(self) -> dict:
        return dict(self.metrics)


def find_node(trip: dict, node_id: str) -> dict:
    for day in trip.get("days", []):
        for node in day.get("nodes", []):
            if node.get("id") == node_id:
                return node
    raise ValueError(f"Node {node_id} not found")


def contextual_research_system_prompt() -> str:
    return (
        "You are the lightweight consultation layer inside a travel Trip Board. "
        "You may use the provided trip, node, and specialist selection context to answer. "
        "Do not modify the trip. Do not create a proposal. Do not say an itinerary has been changed. "
        "Return a practical answer only."
    )


def contextual_research_user_prompt(request: dict) -> str:
    trip = request.get("trip")
    intent = request.get("intent", {})
    node = find_node_or_none(trip, intent.get("node_id")) if trip else None
    return json.dumps(
        {
            "user_message": request.get("user_message", ""),
            "intent": intent,
            "routing": request.get("routing", {}),
            "current_node": node,
            "trip_summary": summarize_trip_for_prompt(trip),
            "output_rule": "Answer only. Do not generate TripProposal or mutate trip.",
        },
        ensure_ascii=False,
    )


def find_node_or_none(trip: dict | None, node_id: str | None) -> dict | None:
    if not trip or not node_id:
        return None
    try:
        return find_node(trip, node_id)
    except ValueError:
        return None


def summarize_trip_for_prompt(trip: dict | None) -> dict | None:
    if not trip:
        return None
    return {
        "id": trip.get("id"),
        "version": trip.get("version"),
        "title": trip.get("title"),
        "days": [
            {
                "id": day.get("id"),
                "title": day.get("title"),
                "nodes": [
                    {
                        "id": node.get("id"),
                        "type": node.get("type"),
                        "title": node.get("title"),
                        "time": node.get("time"),
                    }
                    for node in day.get("nodes", [])
                ],
            }
            for day in trip.get("days", [])
        ],
    }
