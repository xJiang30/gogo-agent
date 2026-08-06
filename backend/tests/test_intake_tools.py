from app.agents.tools.intake import _inspect_intake_fields
from app.schemas.intake import IntakeFields


def test_inspect_intake_fields_reports_missing_fields():
    inspection = _inspect_intake_fields(
        IntakeFields(destination="九州", preferences=["温泉"])
    )

    assert inspection.ready is False
    assert inspection.missing_fields == ["duration", "travelers", "budget"]


def test_inspect_intake_fields_marks_complete_fields_ready():
    inspection = _inspect_intake_fields(
        IntakeFields(
            destination="九州",
            duration="5 天",
            travelers=2,
            budget="¥10,000",
            preferences=["温泉"],
        )
    )

    assert inspection.ready is True
    assert inspection.missing_fields == []
