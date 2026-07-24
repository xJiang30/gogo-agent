from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResearchBrief(BaseModel):
    brief_id: str
    domain: str
    mode: str
    planning_brief: dict
    skeleton_plan: dict
    trip_snapshot: dict | None = None
    constraints: list[str] = Field(default_factory=list)
    max_options: int = 3


class ResearchOption(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    title: str | None = None
    label: str | None = None
    name: str | None = None
    rationale: str | None = None

    def display_title(self) -> str:
        return self.title or self.label or self.name or self.id or "Untitled option"


class ResearchResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    domain: str
    summary: str = ""
    options: list[ResearchOption] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    missing_info: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    confidence: float | None = None
    raw: dict[str, Any] = Field(default_factory=dict)

    @field_validator("options", mode="before")
    @classmethod
    def normalize_options(cls, value):
        if not isinstance(value, list):
            return []
        normalized = []
        for index, item in enumerate(value):
            if isinstance(item, str):
                normalized.append({"id": f"option-{index + 1}", "label": item})
            else:
                normalized.append(item)
        return normalized
