from agents import Runner

from app.agents.travel_advisor import create_travel_advisor
from app.providers.llm import build_run_config
from app.providers.session import generate_session_id, get_agent_session
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
    session_id = request.session_id or generate_session_id()
    result = await Runner.run(
        create_travel_advisor(),
        _build_intake_prompt(request),
        run_config=build_run_config(
            session_id=session_id,
            workflow_name="gogo-agent-intake",
        ),
        session=get_agent_session(session_id),
    )
    response = result.final_output_as(IntakeResponse, raise_if_incorrect_type=True)
    response.session_id = session_id
    return response
