from enum import StrEnum

from pydantic import BaseModel, Field


class ReplanScope(StrEnum):
    INITIAL_PLAN = "initial_plan"
    DISCUSSION_TURN = "discussion_turn"
    LOCAL_NODE_PROPOSAL = "local_node_proposal"
    DAY_REPLAN = "day_replan"
    CROSS_DAY_REPLAN = "cross_day_replan"
    REGENERATE_RECOMMENDATIONS = "regenerate_recommendations"
    LIGHTWEIGHT_RESEARCH = "lightweight_research"


class ReplanNeed(StrEnum):
    STAY = "stay"
    MOBILITY = "mobility"
    EXPERIENCE = "experience"
    WEATHER = "weather"
    TICKET = "ticket"
    FLIGHT = "flight"
    RAIL = "rail"
    PRICE = "price"


class ReplanRoutingDecision(BaseModel):
    scope: ReplanScope
    decision: str
    output_kind: str
    affected_day_ids: list[str] = Field(default_factory=list)
    affected_node_ids: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class SpecialistSelection(BaseModel):
    needs: list[ReplanNeed] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
