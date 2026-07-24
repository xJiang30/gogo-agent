from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class RunMetadata(BaseModel):
    run_id: str
    mode: str
    user_id: str
    conversation_id: str | None = None
    discussion_id: str | None = None
    trip_id: str | None = None
    status: str = "accepted"
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentRunAccepted(BaseModel):
    kind: str = "agent_run_accepted"
    run: RunMetadata
    output: Any


class RunEvent(BaseModel):
    event_id: str
    run_id: str
    type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = Field(default_factory=dict)
