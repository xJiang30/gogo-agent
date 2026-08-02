from agents import Agent

from app.providers.llm import build_litellm_model
from app.schemas.intake import IntakeResponse


def create_travel_advisor() -> Agent:
    return Agent(
        name="TravelAdvisor",
        instructions=(
            "You are Gogo Agent, a lightweight travel planning assistant. "
            "Collect only the missing fields needed to start a trip board: "
            "destination, dates, travelers, budget, and preferences. "
            "Return structured intake results and do not mutate trip state."
        ),
        model=build_litellm_model(),
        output_type=IntakeResponse,
    )
