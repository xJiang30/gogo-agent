from copy import deepcopy
from datetime import datetime, timezone

from backend.agent.contracts.routing_and_proposal import TripProposal

SAFE_NODE_UPDATE_FIELDS = {
    "title",
    "detail",
    "time",
    "location",
    "duration",
    "rationale",
    "notes",
    "area",
    "pace",
}


class ProposalExecutor:
    def execute(self, trip: dict, proposal: TripProposal | dict) -> dict:
        proposal = proposal if isinstance(proposal, TripProposal) else TripProposal.model_validate(proposal)
        if proposal.status != "accepted":
            raise ValueError("Only accepted proposals can be executed")
        if not proposal.operations:
            raise ValueError("Cannot execute a proposal without operations")
        if trip["version"] != proposal.base_version:
            raise ValueError("Trip version mismatch")

        next_trip = deepcopy(trip)

        for operation in proposal.operations:
            if operation.type == "ReplaceNode":
                replace_node(next_trip, operation.day_id, operation.node_id, operation.replacement)
            elif operation.type == "UpdateNode":
                update_node(next_trip, operation.day_id, operation.node_id, operation.patch)
            else:
                raise ValueError(f"Unsupported proposal operation type: {operation.type}")

        next_trip["version"] += 1

        return {
            "trip": next_trip,
            "decisionLog": {
                "proposalId": proposal.proposal_id,
                "tripId": proposal.trip_id,
                "executedAt": datetime.now(timezone.utc).isoformat(),
                "operations": [operation.model_dump() for operation in proposal.operations],
            },
        }


def replace_node(trip: dict, day_id: str | None, node_id: str | None, replacement: dict | None) -> None:
    if not day_id or not node_id or not replacement:
        raise ValueError("ReplaceNode requires day_id, node_id, and replacement")
    for day in trip.get("days", []):
        if day.get("id") != day_id:
            continue
        for index, node in enumerate(day.get("nodes", [])):
            if node.get("id") == node_id:
                day["nodes"][index] = {**node, **safe_node_payload(replacement)}
                return
    raise ValueError(f"ReplaceNode target not found: day_id={day_id}, node_id={node_id}")


def update_node(trip: dict, day_id: str | None, node_id: str | None, patch: dict | None) -> None:
    if not day_id or not node_id or not patch:
        raise ValueError("UpdateNode requires day_id, node_id, and patch")
    for day in trip.get("days", []):
        if day.get("id") != day_id:
            continue
        for node in day.get("nodes", []):
            if node.get("id") == node_id:
                node.update(safe_node_payload(patch))
                return
    raise ValueError(f"UpdateNode target not found: day_id={day_id}, node_id={node_id}")


def safe_node_payload(payload: dict) -> dict:
    return {key: value for key, value in payload.items() if key in SAFE_NODE_UPDATE_FIELDS}
