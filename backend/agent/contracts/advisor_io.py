from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .recommendation_output import RecommendationSet
from .routing_and_proposal import TripProposal
from .trip_board import TripBoardResponse


class TravelAdvisorRequest(BaseModel):
    user_id: str
    conversation_id: str
    user_message: str
    trip: dict[str, Any] | None = None
    intent: dict[str, Any] | None = None


class AnswerResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    kind: str = "answer"
    routing: dict[str, Any]
    planning_brief: dict[str, Any] = Field(alias="planningBrief")
    text: str
    fallback: dict[str, Any] | None = None


class ClarificationQuestionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    kind: str = "clarification_question"
    routing: dict[str, Any]
    planning_brief: dict[str, Any] = Field(alias="planningBrief")
    questions: list[dict[str, Any]]
    text: str
    reason: str | None = None


class ProposalResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    kind: str = "proposal"
    routing: dict[str, Any]
    planning_brief: dict[str, Any] = Field(alias="planningBrief")
    proposal: TripProposal
    frontend_proposal: dict[str, Any] = Field(alias="frontendProposal")


class RecommendationSetResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    kind: str = "recommendation_set"
    routing: dict[str, Any]
    planning_brief: dict[str, Any] = Field(alias="planningBrief")
    recommendation_set: RecommendationSet = Field(alias="recommendationSet")
    trace: list[dict]
