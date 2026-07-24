from datetime import datetime, timezone

from backend.agent.contracts.routing_and_proposal import TripProposal


class ProposalService:
    def __init__(self) -> None:
        self.proposals: dict[str, TripProposal] = {}
        self.histories: dict[str, list[dict]] = {}
        self.allowed_transitions = {
            "pending": {"accepted", "rejected", "expired", "conflicted"},
            "accepted": set(),
            "rejected": set(),
            "expired": set(),
            "conflicted": set(),
        }

    def persist_proposal(self, proposal, *, current_trip_version: int) -> TripProposal:
        parsed = proposal if isinstance(proposal, TripProposal) else TripProposal.model_validate(proposal)
        next_status = "pending" if parsed.base_version == current_trip_version else "conflicted"
        stored = parsed.model_copy(update={"status": next_status})
        self.proposals[stored.proposal_id] = stored
        self.histories[stored.proposal_id] = [create_history_entry(None, next_status)]
        return stored

    def get_proposal(self, proposal_id: str) -> TripProposal | None:
        return self.proposals.get(proposal_id)

    def list_proposals(self) -> list[TripProposal]:
        return list(self.proposals.values())

    def update_proposal_status(self, proposal_id: str, status: str) -> TripProposal | None:
        result = self.try_update_proposal_status(proposal_id, status)
        return result["proposal"] if result["ok"] else None

    def try_update_proposal_status(self, proposal_id: str, status: str) -> dict:
        current = self.proposals.get(proposal_id)
        if not current:
            return {
                "ok": False,
                "error": "proposal_not_found",
                "proposal": None,
            }
        if not self.can_transition(current.status, status):
            return {
                "ok": False,
                "error": "invalid_status_transition",
                "from_status": current.status,
                "to_status": status,
                "proposal": current,
            }
        updated = self.apply_status_update(current, status)
        return {
            "ok": True,
            "error": None,
            "proposal": updated,
        }

    def apply_status_update(self, current: TripProposal, status: str) -> TripProposal:
        updated = current.model_copy(update={"status": status})
        self.proposals[current.proposal_id] = updated
        self.histories.setdefault(current.proposal_id, []).append(create_history_entry(current.status, status))
        return updated

    def get_proposal_history(self, proposal_id: str) -> list[dict]:
        return self.histories.get(proposal_id, [])

    def can_transition(self, from_status: str, to_status: str) -> bool:
        if from_status == to_status:
            return True
        return to_status in self.allowed_transitions.get(from_status, set())


def create_history_entry(from_status: str | None, to_status: str) -> dict:
    return {
        "from_status": from_status,
        "to_status": to_status,
        "changed_at": datetime.now(timezone.utc).isoformat(),
    }
