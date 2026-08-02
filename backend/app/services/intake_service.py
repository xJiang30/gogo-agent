from app.capabilities.intake import intake_is_ready, missing_intake_fields
from app.schemas.intake import IntakeFields, IntakeRequest, IntakeResponse


def collect_trip_intake(request: IntakeRequest) -> IntakeResponse:
    fields = request.fields
    message = request.message

    if "日本" in message or "九州" in message:
        fields.destination = fields.destination or "日本 / 九州"
    if "5-6" in message or "5 到 6" in message:
        fields.duration = fields.duration or "5-6 天"
    if "两个" in message or "2 人" in message or "两个人" in message:
        fields.travelers = fields.travelers or 2
    if "8000" in message or "10000" in message:
        fields.budget = fields.budget or "¥8,000-10,000"

    inferred_preferences = [
        word for word in ("温泉", "美食", "自然", "不赶") if word in message
    ]
    fields.preferences = list(dict.fromkeys([*fields.preferences, *inferred_preferences]))

    missing = missing_intake_fields(fields)
    ready = intake_is_ready(fields)
    assistant_message = (
        "信息够了，可以开始生成 Trip Board。"
        if ready
        else f"还需要补充：{', '.join(missing)}。"
    )
    return IntakeResponse(
        ready=ready,
        fields=fields,
        missing_fields=missing,
        assistant_message=assistant_message,
    )
