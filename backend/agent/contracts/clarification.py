from pydantic import BaseModel, Field


class ClarificationQuestion(BaseModel):
    id: str
    text: str
    required: bool = True
    answer_type: str = "text"


class ClarificationDecision(BaseModel):
    should_ask: bool
    questions: list[ClarificationQuestion] = Field(default_factory=list)
    reason: str | None = None
