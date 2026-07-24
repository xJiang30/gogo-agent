from backend.agent.contracts.graph_state import TripPlanningGraphState
from backend.agent.contracts.errors import GraphErrorEnvelope
from backend.agent.contracts.recommendation_output import RecommendationSet, TripIntent
from backend.agent.contracts.routing_and_proposal import (
    ProposalEvidence,
    ProposalImpact,
    ProposalOperation,
    TripProposal,
)
from backend.agent.providers.errors import LlmProviderError


def finalize_output_node(state: TripPlanningGraphState, provider=None) -> TripPlanningGraphState:
    if state.mode == "cross_day_replan":
        state.final_trip_proposal = build_trip_proposal(state, provider)
    else:
        brief = state.planning_brief
        state.final_recommendation_set = RecommendationSet(
            trip_intent=TripIntent(
                destination=brief.destination_candidates[0] if brief.destination_candidates else None,
                duration_days=brief.duration_days,
                traveler_count=brief.traveler_count,
                budget=brief.budget,
                pace=brief.pace,
                interests=brief.interests,
                origin_message=brief.origin_message,
            ),
            recommendations=state.recommendations[:3],
        )
    state.status = "completed"
    state.trace.append({"node": "finalize_output_node"})
    return state


def build_trip_proposal(state: TripPlanningGraphState, provider=None) -> TripProposal | None:
    trip = state.trip_snapshot or {}
    proposal_id = trip.get("_proposal_id") or "graph_replan-manual"
    affected_day_ids = state.planning_brief.affected_day_ids or []
    affected_node_ids = state.planning_brief.affected_node_ids or []
    if affected_day_ids and not affected_node_ids:
        state.graph_error = GraphErrorEnvelope(
            decision="fail_run",
            retryable=False,
            error_code="replan_requires_target_nodes",
            failed_domains=["cross_day_replan"],
            message="Replan requests must identify the affected nodes before generating executable proposal operations.",
        )
        return None
    target_nodes = collect_target_nodes(trip, affected_day_ids, affected_node_ids)
    if not target_nodes:
        state.graph_error = GraphErrorEnvelope(
            decision="fail_run",
            retryable=False,
            error_code="no_replan_operations",
            failed_domains=["cross_day_replan"],
            message="No matching trip nodes were found for the requested replan.",
        )
        return None
    if not provider or not hasattr(provider, "generate_replan_proposal"):
        state.graph_error = GraphErrorEnvelope(
            decision="retry_later",
            retryable=False,
            error_code="provider_capability_error",
            failed_domains=["cross_day_replan"],
            message="Cross-day replan requires a provider with generate_replan_proposal.",
        )
        return None

    try:
        payload = provider.generate_replan_proposal(
            system_prompt=replan_proposal_system_prompt(),
            user_prompt=replan_proposal_user_prompt(
                state=state,
                target_nodes=target_nodes,
            ),
        )
        proposal = parse_replan_proposal_payload(
            payload,
            proposal_id=proposal_id,
            trip=trip,
            state=state,
            affected_day_ids=affected_day_ids,
            target_nodes=target_nodes,
        )
    except LlmProviderError as error:
        state.graph_error = GraphErrorEnvelope(
            decision="retry_later",
            retryable=error.retryable,
            error_code=error.code,
            failed_domains=["cross_day_replan"],
            message=str(error),
        )
        return None
    except (TypeError, ValueError) as error:
        state.graph_error = GraphErrorEnvelope(
            decision="fail_run",
            retryable=False,
            error_code=type(error).__name__,
            failed_domains=["cross_day_replan"],
            message="Cross-day replan provider returned invalid proposal operations.",
        )
        return None
    return proposal


def parse_replan_proposal_payload(
    payload: dict,
    *,
    proposal_id: str,
    trip: dict,
    state: TripPlanningGraphState,
    affected_day_ids: list[str],
    target_nodes: list[dict],
) -> TripProposal:
    operations = [ProposalOperation.model_validate(item) for item in payload.get("operations", [])]
    if not operations:
        raise ValueError("replan_proposal_requires_operations")
    if not payload.get("title"):
        raise ValueError("replan_proposal_requires_title")
    if not payload.get("summary"):
        raise ValueError("replan_proposal_requires_summary")
    validate_operations_target_nodes(operations, target_nodes)
    return TripProposal(
        proposal_id=proposal_id,
        trip_id=trip.get("id", state.trip_id or "trip"),
        base_version=trip.get("version", 1),
        scope="trip",
        title=payload["title"],
        summary=payload["summary"],
        reasons=payload.get("reasons", []),
        warnings=payload.get("warnings", []),
        operations=operations,
        impact=ProposalImpact(affected_day_ids=affected_day_ids),
        evidence=parse_proposal_evidence(payload.get("evidence", []), proposal_id),
    )


def choose_candidate(state: TripPlanningGraphState):
    passing_ids = {
        item.candidate_id
        for item in (state.validation_result.candidate_results if state.validation_result else [])
        if item.status == "pass"
    }
    candidates = [item for item in state.recommendations if not passing_ids or item.id in passing_ids]
    return sorted(candidates, key=lambda item: item.score or 0, reverse=True)[0]


def collect_target_nodes(
    trip: dict,
    affected_day_ids: list[str],
    affected_node_ids: list[str] | None = None,
) -> list[dict]:
    target_nodes = []
    target_node_ids = set(affected_node_ids or [])
    for day_id in affected_day_ids:
        day = next((item for item in trip.get("days", []) if item.get("id") == day_id), None)
        if not day or not day.get("nodes"):
            continue
        nodes = [node for node in day["nodes"] if node.get("id") in target_node_ids]
        for node in nodes:
            target_nodes.append({"dayId": day_id, "node": node})
    return target_nodes


def validate_operations_target_nodes(operations: list[ProposalOperation], target_nodes: list[dict]) -> None:
    allowed = {(item.get("dayId"), (item.get("node") or {}).get("id")) for item in target_nodes}
    for operation in operations:
        if (operation.day_id, operation.node_id) not in allowed:
            raise ValueError(f"operation_targets_non_target_node: day_id={operation.day_id}, node_id={operation.node_id}")


def parse_proposal_evidence(items, proposal_id: str) -> list[ProposalEvidence]:
    evidence = []
    for index, item in enumerate(items or []):
        if isinstance(item, dict):
            evidence.append(ProposalEvidence.model_validate(item))
        elif isinstance(item, str):
            evidence.append(
                ProposalEvidence(
                    id=f"{proposal_id}-evidence-{index + 1}",
                    kind="planner_note",
                    text=item,
                ),
            )
    return evidence


def replan_proposal_system_prompt() -> str:
    return (
        "You generate safe TripProposal operations for a travel planning agent. Return JSON only. "
        "Use concrete UpdateNode or ReplaceNode operations. Do not return template text. "
        "Every operation must target one of the provided targetNodes."
    )


def replan_proposal_user_prompt(*, state: TripPlanningGraphState, target_nodes: list[dict]) -> str:
    import json

    payload = {
        "userMessage": state.planning_brief.origin_message,
        "planningBrief": state.planning_brief.model_dump(),
        "tripSnapshot": state.trip_snapshot,
        "targetNodes": target_nodes,
        "operationSchema": {
            "UpdateNode": {"type": "UpdateNode", "day_id": "day id", "node_id": "node id", "patch": {"title": "optional", "detail": "concrete new detail"}},
            "ReplaceNode": {"type": "ReplaceNode", "day_id": "day id", "node_id": "node id", "replacement": {"id": "same or new id", "title": "concrete title"}},
        },
    }
    return json.dumps(payload, ensure_ascii=False)
