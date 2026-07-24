from pydantic import BaseModel, Field


class TripIntent(BaseModel):
    destination: str | None = None
    duration_days: int | None = None
    traveler_count: int | None = None
    budget: str | None = None
    pace: str | None = None
    interests: list[str] = Field(default_factory=list)
    origin_message: str = ""


class StayPlan(BaseModel):
    anchor_area: str
    nights: int | None = None
    rationale: str
    hotel_switches: int = 0


class DayTripPlan(BaseModel):
    destination: str
    transport: str | None = None
    estimated_one_way_time: str | None = None
    transfer_pressure: str | None = None
    rationale: str | None = None


class MobilityPlan(BaseModel):
    day_trip: DayTripPlan


class FoodPlan(BaseModel):
    must_try: list[str] = Field(default_factory=list)
    suggested_areas: list[str] = Field(default_factory=list)
    reservation_notes: list[str] = Field(default_factory=list)


class DayBlock(BaseModel):
    time_of_day: str
    type: str
    title: str
    location: str | None = None
    duration: str | None = None
    rationale: str | None = None


class DayPlan(BaseModel):
    day: int
    title: str
    area: str | None = None
    pace: str | None = None
    blocks: list[DayBlock] = Field(default_factory=list)


class TravelPlanRecommendation(BaseModel):
    id: str
    title: str
    theme: str
    summary: str
    best_for: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    confidence: float | None = None
    stay_plan: StayPlan
    day_plans: list[DayPlan] = Field(default_factory=list)
    mobility_plan: MobilityPlan
    food_plan: FoodPlan
    evidence: list[str] = Field(default_factory=list)
    missing_info: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    source: str = "python_langgraph_trip_planning_graph"
    score: float = 0


class RecommendationSet(BaseModel):
    type: str = "recommendation_set"
    version: str = "1.0"
    trip_intent: TripIntent
    recommendations: list[TravelPlanRecommendation]
