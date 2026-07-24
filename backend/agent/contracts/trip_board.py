from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TripBoardResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    kind: str = "trip_board"
    routing: dict[str, Any]
    planning_brief: dict[str, Any] = Field(alias="planningBrief")
    trip: dict[str, Any]
    source_recommendation: dict[str, Any] | None = Field(default=None, alias="sourceRecommendation")
    source_recommendation_set: dict[str, Any] | None = Field(default=None, alias="sourceRecommendationSet")
    evidence: list[Any] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)
