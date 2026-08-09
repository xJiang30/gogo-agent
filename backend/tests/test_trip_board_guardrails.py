import asyncio

from app.agents.guardrails.trip_board import (
    proposal_only_output_guardrail,
    validate_intake_output_is_proposal_safe,
)
from app.agents.travel_advisor import create_travel_advisor
from app.schemas.intake import IntakeFields, IntakeResponse


def test_validate_intake_output_allows_proposal_safe_message():
    result = validate_intake_output_is_proposal_safe(
        IntakeResponse(
            ready=True,
            fields=IntakeFields(
                destination="九州",
                duration="5 天",
                travelers=2,
                budget="¥10,000",
                preferences=["温泉"],
            ),
            missing_fields=[],
            assistant_message="信息够了，可以开始生成 Trip Board。",
        )
    )

    assert result.tripwire_triggered is False


def test_validate_intake_output_blocks_claiming_trip_board_mutation():
    result = validate_intake_output_is_proposal_safe(
        IntakeResponse(
            ready=True,
            fields=IntakeFields(destination="九州"),
            missing_fields=[],
            assistant_message="已帮你应用到 Trip Board，并修改好了第一天路线。",
        )
    )

    assert result.tripwire_triggered is True
    assert "proposal-only" in result.output_info["reason"]


def test_proposal_only_guardrail_wraps_intake_validation():
    output = IntakeResponse(
        ready=True,
        fields=IntakeFields(destination="九州"),
        missing_fields=[],
        assistant_message="已预订酒店。",
    )

    result = asyncio.run(
        proposal_only_output_guardrail.run(None, create_travel_advisor(), output)
    )

    assert result.output.tripwire_triggered is True


def test_travel_advisor_has_proposal_only_output_guardrail():
    agent = create_travel_advisor()

    assert [
        guardrail.get_name() for guardrail in agent.output_guardrails
    ] == ["proposal_only_output_guardrail"]
