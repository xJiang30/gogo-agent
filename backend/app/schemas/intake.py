from pydantic import BaseModel, Field


class IntakeFields(BaseModel):
    destination: str | None = None
    duration: str | None = None
    travelers: int | None = Field(default=None, ge=1)
    budget: str | None = None
    preferences: list[str] = Field(default_factory=list)


class IntakeRequest(BaseModel):
    message: str
    session_id: str | None = None
    fields: IntakeFields = Field(default_factory=IntakeFields)


class IntakeResponse(BaseModel):
    ready: bool
    session_id: str | None = None
    fields: IntakeFields
    missing_fields: list[str]
    assistant_message: str


class IntakeInspection(BaseModel):
    ready: bool
    missing_fields: list[str]
