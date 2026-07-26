from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class EscalationDecision(StrEnum):
    DIRECT_ANSWER = "direct_answer"
    LIGHTWEIGHT_RESEARCH = "lightweight_research"
    GRAPH_REPLAN = "graph_replan"
    REGENERATE_RECOMMENDATIONS = "regenerate_recommendations"


class ProposalOperation(BaseModel):
    type: str
    day_id: str | None = None
    node_id: str | None = None
    patch: dict[str, Any] | None = None
    replacement: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_operation_payload(self):
        if self.type == "ReplaceNode":
            if not self.day_id or not self.node_id or not self.replacement:
                raise ValueError("ReplaceNode requires day_id, node_id, and replacement")
            return self
        if self.type == "UpdateNode":
            if not self.day_id or not self.node_id or not self.patch:
                raise ValueError("UpdateNode requires day_id, node_id, and patch")
            return self
        raise ValueError(f"Unsupported proposal operation type: {self.type}")


class ProposalImpact(BaseModel):
    affected_day_ids: list[str] = Field(default_factory=list)
    requires_recalc_segment_ids: list[str] = Field(default_factory=list)


class ProposalEvidence(BaseModel):
    id: str
    kind: str
    text: str


class TripProposal(BaseModel):
    proposal_id: str
    trip_id: str
    base_version: int
    scope: str
    title: str
    summary: str
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    operations: list[ProposalOperation]
    impact: ProposalImpact = Field(default_factory=ProposalImpact)
    evidence: list[ProposalEvidence] = Field(default_factory=list)
    status: str = "draft"

    @field_validator("operations")
    @classmethod
    def operations_must_not_be_empty(cls, value: list[ProposalOperation]) -> list[ProposalOperation]:
        if not value:
            raise ValueError("TripProposal requires at least one operation")
        return value
