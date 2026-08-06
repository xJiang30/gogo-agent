from agents import Runner

from app.agents.travel_advisor import create_travel_advisor
from app.providers.llm import build_run_config
from app.schemas.intake import IntakeRequest, IntakeResponse


def _build_intake_prompt(request: IntakeRequest) -> str:
    return (
        "Collect travel intake fields from the user's latest message. "
        "Use the current fields as already-known context, ask only for missing "
        "required information, and return an IntakeResponse.\n\n"
        f"Current intake fields:\n{request.fields.model_dump_json()}\n\n"
        f"User message:\n{request.message}"
    )


async def collect_trip_intake(request: IntakeRequest) -> IntakeResponse:
    result = await Runner.run(
        create_travel_advisor(),
        _build_intake_prompt(request),
        run_config=build_run_config(),
    )
    return result.final_output_as(IntakeResponse, raise_if_incorrect_type=True)
