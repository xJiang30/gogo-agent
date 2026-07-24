from pydantic import BaseModel, Field


class GraphErrorEnvelope(BaseModel):
    layer: str = "graph"
    decision: str
    retryable: bool
    error_code: str | None = None
    failed_domains: list[str] = Field(default_factory=list)
    message: str
    provider_status: int | None = None


class AdvisorFallbackDecision(BaseModel):
    layer: str = "advisor"
    decision: str
    message: str
    source: str = "graph"
    retryable: bool
    graph_error: GraphErrorEnvelope | None = None
    missing: list[str] = Field(default_factory=list)
    error: str | None = None
    error_code: str | None = None
    reason: str | None = None
