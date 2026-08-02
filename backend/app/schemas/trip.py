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
