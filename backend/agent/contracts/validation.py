from pydantic import BaseModel, Field


class CandidateValidationResult(BaseModel):
    candidate_id: str
    status: str
    reasons: list[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    candidate_results: list[CandidateValidationResult] = Field(default_factory=list)
    overall_status: str
