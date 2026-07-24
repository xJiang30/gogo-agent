from pydantic import BaseModel

from .research import ResearchResult


class ResearchOutcome(BaseModel):
    domain: str
    status: str
    result: ResearchResult | None = None
    reason: str | None = None
    retryable: bool = False
    error_code: str | None = None
