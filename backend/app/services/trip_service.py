from uuid import uuid4

from app.schemas.trip import (
    ApplyProposalRequest,
    ApplyProposalResponse,
    CreateProposalRequest,
    StartPlanRequest,
    TripBoard,
    TripBoardProposal,
    TripDay,
    TripNode,
)


class TripNotFoundError(LookupError):
    pass


class ProposalNotFoundError(LookupError):
    pass


class ProposalApprovalRequiredError(ValueError):
    pass


class ProposalAlreadyAppliedError(ValueError):
    pass


TRIP_BOARDS: dict[str, TripBoard] = {}
TRIP_BOARD_PROPOSALS: dict[str, TripBoardProposal] = {}


def clear_trip_state() -> None:
    TRIP_BOARDS.clear()
    TRIP_BOARD_PROPOSALS.clear()


def start_plan(request: StartPlanRequest) -> TripBoard:
    destination = request.intake.destination or "未命名目的地"
    board = TripBoard(
        id="trip-demo-kyushu",
        title=f"{destination} 轻量行程",
        destination=destination,
        days=[
            TripDay(
                id="day-1",
                title="Day 1",
                nodes=[
                    TripNode(
                        id="arrival",
                        title="抵达并入住",
                        kind="arrival",
                        starts_at="15:00",
                        notes="先保持落地日轻松，后续由 Trip Board 细化。",
                    )
                ],
            )
        ],
    )
    TRIP_BOARDS[board.id] = board
    return board


def create_trip_board_proposal(
    trip_id: str,
    request: CreateProposalRequest,
) -> TripBoardProposal:
    if trip_id not in TRIP_BOARDS:
        raise TripNotFoundError(f"Trip board not found: {trip_id}")

    proposal = TripBoardProposal(
        id=f"proposal-{uuid4().hex}",
        trip_id=trip_id,
        status="pending",
        requires_approval=True,
        summary=request.summary,
        mutations=request.mutations,
    )
    TRIP_BOARD_PROPOSALS[proposal.id] = proposal
    return proposal


def apply_trip_board_proposal(
    trip_id: str,
    proposal_id: str,
    request: ApplyProposalRequest,
) -> ApplyProposalResponse:
    if not request.approved:
        raise ProposalApprovalRequiredError("Proposal requires explicit approval.")

    board = TRIP_BOARDS.get(trip_id)
    if board is None:
        raise TripNotFoundError(f"Trip board not found: {trip_id}")

    proposal = TRIP_BOARD_PROPOSALS.get(proposal_id)
    if proposal is None or proposal.trip_id != trip_id:
        raise ProposalNotFoundError(f"Proposal not found: {proposal_id}")
    if proposal.status == "applied":
        raise ProposalAlreadyAppliedError(f"Proposal already applied: {proposal_id}")

    for mutation in proposal.mutations:
        if mutation.action == "add_node":
            _apply_add_node(board, mutation.day_id, mutation.node)

    proposal.status = "applied"
    proposal.requires_approval = False
    TRIP_BOARD_PROPOSALS[proposal.id] = proposal

    return ApplyProposalResponse(
        proposal=proposal,
        trip_board=board,
        assistant_message="已应用。",
    )


def _apply_add_node(board: TripBoard, day_id: str, node: TripNode) -> None:
    for day in board.days:
        if day.id == day_id:
            day.nodes.append(node)
            return
    raise ValueError(f"Trip day not found: {day_id}")
