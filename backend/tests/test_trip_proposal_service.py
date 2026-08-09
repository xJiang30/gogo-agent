import pytest

from app.schemas.intake import IntakeFields
from app.schemas.trip import (
    ApplyProposalRequest,
    CreateProposalRequest,
    StartPlanRequest,
    TripBoardMutation,
    TripNode,
)
from app.services import trip_service


@pytest.fixture(autouse=True)
def clear_trip_state():
    trip_service.clear_trip_state()


def test_create_trip_board_proposal_requires_user_approval():
    board = trip_service.start_plan(
        StartPlanRequest(intake=IntakeFields(destination="九州"))
    )

    proposal = trip_service.create_trip_board_proposal(
        board.id,
        CreateProposalRequest(
            summary="把晚餐提前，让落地日更松。",
            mutations=[
                TripBoardMutation(
                    action="add_node",
                    day_id="day-1",
                    node=TripNode(
                        id="early-dinner",
                        title="提前晚餐",
                        kind="meal",
                        starts_at="17:45",
                    ),
                )
            ],
        ),
    )

    assert proposal.trip_id == board.id
    assert proposal.status == "pending"
    assert proposal.requires_approval is True


def test_apply_trip_board_proposal_requires_explicit_approval():
    board = trip_service.start_plan(
        StartPlanRequest(intake=IntakeFields(destination="九州"))
    )
    proposal = trip_service.create_trip_board_proposal(
        board.id,
        CreateProposalRequest(
            summary="加一个晚餐节点。",
            mutations=[
                TripBoardMutation(
                    action="add_node",
                    day_id="day-1",
                    node=TripNode(
                        id="dinner",
                        title="天神拉面晚餐",
                        kind="meal",
                        starts_at="18:30",
                    ),
                )
            ],
        ),
    )

    with pytest.raises(trip_service.ProposalApprovalRequiredError):
        trip_service.apply_trip_board_proposal(
            board.id,
            proposal.id,
            ApplyProposalRequest(approved=False),
        )


def test_apply_trip_board_proposal_mutates_board_once_after_approval():
    board = trip_service.start_plan(
        StartPlanRequest(intake=IntakeFields(destination="九州"))
    )
    proposal = trip_service.create_trip_board_proposal(
        board.id,
        CreateProposalRequest(
            summary="加一个晚餐节点。",
            mutations=[
                TripBoardMutation(
                    action="add_node",
                    day_id="day-1",
                    node=TripNode(
                        id="dinner",
                        title="天神拉面晚餐",
                        kind="meal",
                        starts_at="18:30",
                    ),
                )
            ],
        ),
    )

    response = trip_service.apply_trip_board_proposal(
        board.id,
        proposal.id,
        ApplyProposalRequest(approved=True),
    )

    assert response.proposal.status == "applied"
    assert response.assistant_message == "已应用。"
    assert [node.id for node in response.trip_board.days[0].nodes] == [
        "arrival",
        "dinner",
    ]

    with pytest.raises(trip_service.ProposalAlreadyAppliedError):
        trip_service.apply_trip_board_proposal(
            board.id,
            proposal.id,
            ApplyProposalRequest(approved=True),
        )
