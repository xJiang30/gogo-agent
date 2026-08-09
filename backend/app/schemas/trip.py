from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.intake import IntakeFields


class StartPlanRequest(BaseModel):
    intake: IntakeFields


class TripNode(BaseModel):
    id: str
    title: str
    kind: str
    starts_at: str
    notes: str | None = None


class TripDay(BaseModel):
    id: str
    title: str
    nodes: list[TripNode] = Field(default_factory=list)


class TripBoard(BaseModel):
    id: str
    title: str
    destination: str
    days: list[TripDay]


class TripBoardMutation(BaseModel):
    action: Literal["add_node"]
    day_id: str
    node: TripNode


class CreateProposalRequest(BaseModel):
    summary: str
    mutations: list[TripBoardMutation]


class TripBoardProposal(BaseModel):
    id: str
    trip_id: str
    status: Literal["pending", "applied", "rejected"]
    requires_approval: bool = True
    summary: str
    mutations: list[TripBoardMutation]


class ApplyProposalRequest(BaseModel):
    approved: bool


class ApplyProposalResponse(BaseModel):
    proposal: TripBoardProposal
    trip_board: TripBoard
    assistant_message: str
