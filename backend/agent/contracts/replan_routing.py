from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class ReplanScope(StrEnum):
    INITIAL_PLAN = "initial_plan"
    DISCUSSION_TURN = "discussion_turn"
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
    required: list[ReplanNeed] = Field(default_factory=list)
    optional: list[ReplanNeed] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    execution_mode: str = "lightweight"

    @model_validator(mode="after")
    def sync_needs_union(self):
        if self.needs and not self.required and not self.optional:
            self.optional = unique_needs(self.needs)
        merged = unique_needs([*self.required, *self.optional, *self.needs])
        self.needs = merged
        return self


def unique_needs(needs: list[ReplanNeed]) -> list[ReplanNeed]:
    unique: list[ReplanNeed] = []
    for need in needs:
        if need not in unique:
            unique.append(need)
    return unique
