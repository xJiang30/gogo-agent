import operator
from typing import Annotated

from pydantic import BaseModel, Field

from .planning import PlanningBrief
from .recommendation_output import RecommendationSet, TravelPlanRecommendation
from .research import ResearchResult
from .research_outcome import ResearchOutcome
from .errors import GraphErrorEnvelope
from .routing_and_proposal import TripProposal
from .validation import ValidationResult


def keep_first_graph_error(left: GraphErrorEnvelope | None, right: GraphErrorEnvelope | None) -> GraphErrorEnvelope | None:
    return left or right


class TripPlanningGraphState(BaseModel):
    run_id: str
    trip_id: str | None = None
    mode: str
    planning_brief: PlanningBrief
    trip_snapshot: dict | None = None
    skeleton_plan: dict | None = None
    stay_outcome: ResearchOutcome | None = None
    mobility_outcome: ResearchOutcome | None = None
    experience_outcome: ResearchOutcome | None = None
    stay_result: ResearchResult | None = None
    mobility_result: ResearchResult | None = None
    experience_result: ResearchResult | None = None
    candidate_context: dict | None = None
    recommendations: list[TravelPlanRecommendation] = Field(default_factory=list)
    validation_result: ValidationResult | None = None
    final_recommendation_set: RecommendationSet | None = None
    final_trip_proposal: TripProposal | None = None
    trace: Annotated[list[dict], operator.add] = Field(default_factory=list)
    status: str = "running"
    error: str | None = None
    graph_error: Annotated[GraphErrorEnvelope | None, keep_first_graph_error] = None
