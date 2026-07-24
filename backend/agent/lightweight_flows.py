import json

from pydantic import ValidationError

from backend.agent.contracts.routing_and_proposal import ProposalEvidence, ProposalImpact, ProposalOperation, TripProposal
from backend.agent.providers.errors import LlmProviderError


class LightweightFlows:
    def __init__(self, provider=None) -> None:
        self.provider = provider
        self.metrics = {
            "direct_answer_count": 0,
            "lightweight_research_count": 0,
            "local_proposal_count": 0,
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

    def local_proposal(self, request: dict) -> dict:
        self.metrics["local_proposal_count"] += 1
        trip = request["trip"]
        intent = request["intent"]
        node = find_node(trip, intent["node_id"])
        day_id = find_day_id(trip, node["id"])
        affected_day_ids = intent.get("affected_day_ids") or [day_id]

        if not self.provider or not hasattr(self.provider, "generate_local_proposal"):
            raise LlmProviderError(
                code="provider_capability_error",
                message="Local proposal requires a provider with generate_local_proposal",
                retryable=False,
            )

        try:
            payload = self.provider.generate_local_proposal(
                system_prompt=local_proposal_system_prompt(),
                user_prompt=local_proposal_user_prompt(request=request, node=node, day_id=day_id),
            )
            validate_local_proposal_payload(payload)
            replacement = parse_local_replacement(payload)
            evidence = parse_local_evidence(payload.get("evidence", []), request["proposal_id"])
        except LlmProviderError:
            raise
        except (ValidationError, TypeError, ValueError) as error:
            raise LlmProviderError(
                code="provider_response_error",
                message="Local proposal provider returned invalid proposal JSON",
                retryable=False,
                details=str(error),
            ) from error

        return {
            "kind": "proposal",
            "proposal": TripProposal(
                proposal_id=request["proposal_id"],
                trip_id=trip["id"],
                base_version=trip["version"],
                scope=intent.get("scope", "node"),
                title=payload["title"],
                summary=payload["summary"],
                reasons=payload.get("reasons", []),
                warnings=payload.get("warnings", []),
                operations=[
                    ProposalOperation(
                        type="ReplaceNode",
                        day_id=day_id,
                        node_id=node["id"],
                        replacement={
                            **node,
                            **replacement,
                            "booked": False,
                        },
                    ),
                ],
                impact=ProposalImpact(
                    affected_day_ids=affected_day_ids,
                    requires_recalc_segment_ids=[node["id"]] if node.get("type") == "transport" else [],
                ),
                evidence=evidence,
            ),
        }

    def get_metrics(self) -> dict:
        return dict(self.metrics)


def find_node(trip: dict, node_id: str) -> dict:
    for day in trip.get("days", []):
        for node in day.get("nodes", []):
            if node.get("id") == node_id:
                return node
    raise ValueError(f"Node {node_id} not found")


def find_day_id(trip: dict, node_id: str) -> str:
    for day in trip.get("days", []):
        if any(node.get("id") == node_id for node in day.get("nodes", [])):
            return day["id"]
    raise ValueError(f"Day for node {node_id} not found")


def parse_local_replacement(payload: dict) -> dict:
    replacement = payload.get("replacement")
    if not isinstance(replacement, dict) or not replacement.get("title"):
        raise ValueError("local_proposal_requires_replacement_title")
    return replacement


def validate_local_proposal_payload(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise ValueError("local_proposal_requires_object_payload")
    if not payload.get("title"):
        raise ValueError("local_proposal_requires_title")
    if not payload.get("summary"):
        raise ValueError("local_proposal_requires_summary")


def parse_local_evidence(items, proposal_id: str) -> list[ProposalEvidence]:
    evidence = []
    for index, item in enumerate(items or []):
        if isinstance(item, dict):
            evidence.append(ProposalEvidence.model_validate(item))
        elif isinstance(item, str):
            evidence.append(ProposalEvidence(id=f"{proposal_id}-evidence-{index + 1}", kind="planner_note", text=item))
    return evidence


def local_proposal_system_prompt() -> str:
    return (
        "You generate a concrete local TripProposal replacement for one travel itinerary node. Return JSON only. "
        "Do not return placeholder text. Do not claim booking availability. "
        "Required JSON fields: title, summary, reasons, warnings, replacement, evidence. "
        "replacement must include at least title and detail."
    )


def local_proposal_user_prompt(*, request: dict, node: dict, day_id: str) -> str:
    return json.dumps(
        {
            "user_message": request.get("user_message", ""),
            "intent": request.get("intent", {}),
            "day_id": day_id,
            "current_node": node,
            "replacement_schema": {
                "title": "concrete replacement title",
                "detail": "concrete replacement detail",
                "location": "optional location",
                "duration": "optional duration",
            },
        },
        ensure_ascii=False,
    )


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
