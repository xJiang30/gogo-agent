from fastapi import APIRouter, HTTPException

from app.schemas.trip import (
    ApplyProposalRequest,
    ApplyProposalResponse,
    CreateProposalRequest,
    StartPlanRequest,
    TripBoard,
    TripBoardProposal,
)
from app.services.trip_service import (
    ProposalAlreadyAppliedError,
    ProposalApprovalRequiredError,
    ProposalNotFoundError,
    TripNotFoundError,
    apply_trip_board_proposal,
    create_trip_board_proposal,
    start_plan,
)

router = APIRouter()


@router.post("/start-plan", response_model=TripBoard)
def create_trip_board(request: StartPlanRequest) -> TripBoard:
    return start_plan(request)


@router.post("/{trip_id}/proposals", response_model=TripBoardProposal)
def create_proposal(
    trip_id: str,
    request: CreateProposalRequest,
) -> TripBoardProposal:
    try:
        return create_trip_board_proposal(trip_id, request)
    except TripNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/{trip_id}/proposals/{proposal_id}/apply",
    response_model=ApplyProposalResponse,
)
def apply_proposal(
    trip_id: str,
    proposal_id: str,
    request: ApplyProposalRequest,
) -> ApplyProposalResponse:
    try:
        return apply_trip_board_proposal(trip_id, proposal_id, request)
    except ProposalApprovalRequiredError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except (TripNotFoundError, ProposalNotFoundError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ProposalAlreadyAppliedError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
