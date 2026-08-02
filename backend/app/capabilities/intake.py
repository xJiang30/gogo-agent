from app.schemas.intake import IntakeFields


REQUIRED_INTAKE_FIELDS = (
    "destination",
    "duration",
    "travelers",
    "budget",
    "preferences",
)


def missing_intake_fields(fields: IntakeFields) -> list[str]:
    values = fields.model_dump()
    return [name for name in REQUIRED_INTAKE_FIELDS if not values.get(name)]


def intake_is_ready(fields: IntakeFields) -> bool:
    return len(missing_intake_fields(fields)) == 0
