from agents import Agent

from app.agents.guardrails.trip_board import proposal_only_output_guardrail
from app.agents.tools.intake import inspect_intake_fields
from app.schemas.intake import IntakeResponse


def create_travel_advisor() -> Agent:
    return Agent(
        name="TravelAdvisor",
        instructions=(
            "You are Gogo Agent, a lightweight travel planning assistant. "
            "Collect only the missing fields needed to start a trip board: "
            "destination, dates, travelers, budget, and preferences. "
            "Use inspect_intake_fields before your final response to verify "
            "whether the fields are ready. Return structured intake results "
            "and do not mutate trip state."
        ),
        tools=[inspect_intake_fields],
        output_guardrails=[proposal_only_output_guardrail],
        output_type=IntakeResponse,
    )
