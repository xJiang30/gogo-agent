from pydantic import BaseModel, Field


class PlanningBrief(BaseModel):
    mode: str
    origin_message: str
    builder_source: str | None = None
    builder_fallback_reason: str | None = None
    traveler_count: int | None = None
    date_range: str | None = None
    duration_days: int | None = None
    budget: str | None = None
    pace: str | None = None
    destination_candidates: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    dislikes: list[str] = Field(default_factory=list)
    hard_constraints: list[str] = Field(default_factory=list)
    soft_preferences: list[str] = Field(default_factory=list)
    affected_day_ids: list[str] = Field(default_factory=list)
    affected_node_ids: list[str] = Field(default_factory=list)


class TripPlanningGraphRequest(BaseModel):
    run_id: str
    user_id: str
    trip_id: str | None = None
    mode: str
    planning_brief: PlanningBrief
    trip_snapshot: dict | None = None
    constraints: list[str] = Field(default_factory=list)
    preferences: list[str] = Field(default_factory=list)
