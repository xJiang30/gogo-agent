import asyncio
from types import SimpleNamespace

import pytest

from app.schemas.intake import IntakeFields, IntakeRequest, IntakeResponse
from app.services import intake_service


def test_collect_trip_intake_returns_agent_structured_output(monkeypatch):
    expected_session = object()
    expected = IntakeResponse(
        ready=True,
        session_id="trip-session-1",
        fields=IntakeFields(
            destination="日本 / 九州",
            duration="5-6 天",
            travelers=2,
            budget="¥8,000-10,000",
            preferences=["温泉", "美食", "自然", "不赶"],
        ),
        missing_fields=[],
        assistant_message="信息够了，可以开始生成 Trip Board。",
    )

    async def run_agent(agent, input, *, run_config, session):
        assert agent.name == "TravelAdvisor"
        assert '"destination":null' in input
        assert '"preferences":[]' in input
        assert (
            "我想 9 月从上海出发去日本 5-6 天，两个人，预算 8000-10000，"
            "想要温泉、美食、自然风景，不想每天太赶。"
        ) in input
        assert run_config == "test-run-config"
        assert session is expected_session
        return SimpleNamespace(
            final_output_as=lambda cls, raise_if_incorrect_type=False: expected
        )

    monkeypatch.setattr(intake_service.Runner, "run", run_agent)
    monkeypatch.setattr(
        intake_service, "build_run_config", lambda: "test-run-config"
    )
    monkeypatch.setattr(
        intake_service, "get_agent_session", lambda session_id: expected_session
    )

    response = asyncio.run(
        intake_service.collect_trip_intake(
            IntakeRequest(
                session_id="trip-session-1",
                message=(
                    "我想 9 月从上海出发去日本 5-6 天，两个人，预算 8000-10000，"
                    "想要温泉、美食、自然风景，不想每天太赶。"
                )
            )
        )
    )

    assert response == expected


def test_collect_trip_intake_generates_session_id_when_missing(monkeypatch):
    expected_session = object()
    expected = IntakeResponse(
        ready=False,
        fields=IntakeFields(destination="九州"),
        missing_fields=["duration", "travelers", "budget", "preferences"],
        assistant_message="还需要补充时间、人数、预算和偏好。",
    )
    session_ids = []

    async def run_agent(agent, input, *, run_config, session):
        assert session is expected_session
        return SimpleNamespace(
            final_output_as=lambda cls, raise_if_incorrect_type=False: expected
        )

    def get_session(session_id):
        session_ids.append(session_id)
        return expected_session

    monkeypatch.setattr(intake_service.Runner, "run", run_agent)
    monkeypatch.setattr(
        intake_service, "build_run_config", lambda: "test-run-config"
    )
    monkeypatch.setattr(intake_service, "generate_session_id", lambda: "generated-1")
    monkeypatch.setattr(intake_service, "get_agent_session", get_session)

    response = asyncio.run(
        intake_service.collect_trip_intake(
            IntakeRequest(message="我想去九州，帮我慢慢问。")
        )
    )

    assert response.session_id == "generated-1"
    assert session_ids == ["generated-1"]


def test_collect_trip_intake_rejects_non_intake_agent_output(monkeypatch):
    class WrongOutputResult:
        def final_output_as(self, cls, raise_if_incorrect_type=False):
            if raise_if_incorrect_type:
                raise TypeError("Final output is not of type IntakeResponse")
            return {"assistant_message": "looks fine but is not structured"}

    async def run_agent(agent, input, *, run_config, session):
        return WrongOutputResult()

    monkeypatch.setattr(intake_service.Runner, "run", run_agent)
    monkeypatch.setattr(
        intake_service, "build_run_config", lambda: "test-run-config"
    )
    monkeypatch.setattr(
        intake_service, "get_agent_session", lambda session_id: object()
    )

    with pytest.raises(TypeError):
        asyncio.run(
            intake_service.collect_trip_intake(
                IntakeRequest(message="帮我规划一趟轻松的九州旅行")
            )
        )
