from agents import function_tool

from app.capabilities.intake import intake_is_ready, missing_intake_fields
from app.schemas.intake import IntakeFields, IntakeInspection


def _inspect_intake_fields(fields: IntakeFields) -> IntakeInspection:
    return IntakeInspection(
        ready=intake_is_ready(fields),
        missing_fields=missing_intake_fields(fields),
    )


@function_tool
def inspect_intake_fields(fields: IntakeFields) -> IntakeInspection:
    """Check whether the current travel intake fields are ready for a trip board."""
    return _inspect_intake_fields(fields)
