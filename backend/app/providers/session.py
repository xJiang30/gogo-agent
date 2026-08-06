from pathlib import Path
from uuid import uuid4

from agents import SQLiteSession

from app.core.config import get_settings


def generate_session_id() -> str:
    return uuid4().hex


def get_agent_session(session_id: str) -> SQLiteSession:
    db_path = Path(get_settings().agent_session_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return SQLiteSession(session_id=session_id, db_path=db_path)
