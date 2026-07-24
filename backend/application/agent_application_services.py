from datetime import datetime

from backend.agent.graph import TripPlanningGraph
from backend.agent.proposal_executor import ProposalExecutor
from backend.agent.proposal_service import ProposalService
from backend.agent.travel_advisor import TravelAdvisor


class AgentApplicationServices:
    def __init__(
        self,
        *,
        graph: TripPlanningGraph | None = None,
        advisor: TravelAdvisor | None = None,
        proposal_service: ProposalService | None = None,
    ) -> None:
        self.proposal_service = proposal_service or ProposalService()
        self.graph = graph or TripPlanningGraph()
        self.advisor = advisor or TravelAdvisor(
            graph=self.graph,
            proposal_service=self.proposal_service,
            executor=ProposalExecutor(),
        )

    def start_initial_plan_run(self, command: dict) -> dict:
        output = self.advisor.handle_request(
            user_id=command["user_id"],
            conversation_id=command["conversation_id"],
            user_message=command["user_message"],
            trip=None,
            intent={
                "kind": "initial_plan",
                "scope": "trip",
                "affected_day_ids": [],
                "can_close_locally": False,
                "destination_candidates": [],
            },
        )
        return agent_run_accepted(
            run_metadata(
                run_id=create_run_id("initial-plan"),
                mode="initial_plan",
                conversation_id=command["conversation_id"],
                user_id=command["user_id"],
            ),
            output,
        )

    def handle_discussion_turn(self, command: dict) -> dict:
        output = self.advisor.handle_request(
            user_id=command["user_id"],
            conversation_id=command["discussion_id"],
            user_message=command["user_message"],
            trip=command["trip"],
            intent=command["intent"],
        )
        return agent_run_accepted(
            run_metadata(
                run_id=create_run_id("discussion"),
                mode="discussion_turn",
                conversation_id=command["discussion_id"],
                discussion_id=command["discussion_id"],
                trip_id=command["trip"]["id"],
                user_id=command["user_id"],
            ),
            output,
        )

    def execute_proposal(self, command: dict) -> dict:
        return self.advisor.execute_proposal(
            trip=command["trip"],
            proposal_id=command["proposal_id"],
        )

    def set_proposal_status(self, proposal_id: str, status: str):
        return self.proposal_service.try_update_proposal_status(proposal_id, status)


def create_run_id(prefix: str) -> str:
    return f"{prefix}-{int(datetime.now().timestamp() * 1000)}"


def run_metadata(**kwargs) -> dict:
    return {
        "status": "accepted",
        "started_at": datetime.now().isoformat(),
        **kwargs,
    }


def agent_run_accepted(run: dict, output: dict) -> dict:
    return {
        "kind": "agent_run_accepted",
        "run": run,
        "output": output,
    }
