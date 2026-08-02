from app.schemas.intake import IntakeRequest
from app.services.intake_service import collect_trip_intake


def test_collect_trip_intake_marks_ready_when_required_fields_are_present():
    response = collect_trip_intake(
        IntakeRequest(
            message=(
                "我想 9 月从上海出发去日本 5-6 天，两个人，预算 8000-10000，"
                "想要温泉、美食、自然风景，不想每天太赶。"
            )
        )
    )

    assert response.ready is True
    assert response.fields.destination == "日本 / 九州"
    assert response.fields.travelers == 2
    assert response.missing_fields == []
