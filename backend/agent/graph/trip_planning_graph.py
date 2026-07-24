from backend.agent.contracts.graph_state import TripPlanningGraphState
from backend.agent.contracts.errors import GraphErrorEnvelope
from backend.agent.contracts.planning import PlanningBrief, TripPlanningGraphRequest
from backend.agent.planning_brief_builder import PlanningBriefBuilder
from langgraph.graph import END, START, StateGraph

from backend.agent.nodes import (
    candidate_merge_node,
    experience_research_node,
    finalize_output_node,
    mobility_research_node,
    recommendation_planner_node,
    skeleton_planning_node,
    stay_research_node,
    validate_candidates_node,
)
from backend.agent.providers import QwenResearchProvider


class TripPlanningGraph:
    """Python LangGraph implementation for initial trip recommendations."""

    def __init__(self, provider=None) -> None:
        self.provider = provider or QwenResearchProvider()
        self.planning_brief_builder = PlanningBriefBuilder(provider=self.provider)
        self.graph = self._compile_graph()

    def run_initial_plan(
        self,
        user_message: str,
        user_id: str = "manual-user",
        planning_brief: PlanningBrief | None = None,
    ) -> dict:
        request = TripPlanningGraphRequest(
            run_id="manual-run",
            user_id=user_id,
            mode="initial_plan",
            planning_brief=planning_brief or self.planning_brief_builder.build_initial_planning_brief(user_message),
        )
        state = self.run(request)
        if state.graph_error:
            return {
                "kind": "graph_error",
                "graphError": state.graph_error.model_dump(),
                "trace": state.trace,
            }
        return {
            "kind": "recommendation_set",
            "recommendationSet": state.final_recommendation_set.model_dump(by_alias=True),
            "trace": state.trace,
        }

    def run_replan(
        self,
        *,
        user_message: str,
        trip: dict,
        intent: dict,
        user_id: str = "manual-user",
        proposal_id: str = "graph_replan-manual",
    ) -> dict:
        request = TripPlanningGraphRequest(
            run_id="manual-replan-run",
            user_id=user_id,
            trip_id=trip.get("id"),
            mode="cross_day_replan",
            planning_brief=PlanningBrief(
                mode="cross_day_replan",
                origin_message=user_message,
                affected_day_ids=intent.get("affected_day_ids", []),
                affected_node_ids=get_affected_node_ids(intent),
            ),
            trip_snapshot={**trip, "_proposal_id": proposal_id},
        )
        state = self.run(request)
        if state.graph_error:
            return {
                "kind": "graph_error",
                "graphError": state.graph_error.model_dump(),
                "trace": state.trace,
            }
        if not state.final_trip_proposal or not state.final_trip_proposal.operations:
            return {
                "kind": "graph_error",
                "graphError": GraphErrorEnvelope(
                    decision="fail_run",
                    retryable=False,
                    error_code="no_replan_operations",
                    failed_domains=["cross_day_replan"],
                    message="No matching trip nodes were found for the requested replan.",
                ).model_dump(),
                "trace": state.trace,
            }
        return {
            "kind": "proposal",
            "proposal": state.final_trip_proposal.model_dump(),
            "trace": state.trace,
        }

    def run(self, request: TripPlanningGraphRequest) -> TripPlanningGraphState:
        state = TripPlanningGraphState(
            run_id=request.run_id,
            trip_id=request.trip_id,
            mode=request.mode,
            planning_brief=request.planning_brief,
            trip_snapshot=request.trip_snapshot,
        )
        result = self.graph.invoke(state)
        return TripPlanningGraphState.model_validate(result)

    def _compile_graph(self):
        builder = StateGraph(TripPlanningGraphState)
        builder.add_node("skeleton_planning", skeleton_planning_update)
        builder.add_node("stay_research", lambda state: stay_research_update(state, self.provider))
        builder.add_node("mobility_research", lambda state: mobility_research_update(state, self.provider))
        builder.add_node("experience_research", lambda state: experience_research_update(state, self.provider))
        builder.add_node("research_barrier", research_barrier_node)
        builder.add_node("candidate_merge", candidate_merge_update)
        builder.add_node("recommendation_planner", lambda state: recommendation_planner_update(state, self.provider))
        builder.add_node("validate_candidates", validate_candidates_update)
        builder.add_node("finalize_output", lambda state: finalize_output_update(state, self.provider))

        builder.add_conditional_edges(START, route_from_start, {"initial_plan": "skeleton_planning", "cross_day_replan": "finalize_output"})
        builder.add_edge("skeleton_planning", "stay_research")
        builder.add_edge("skeleton_planning", "mobility_research")
        builder.add_edge("skeleton_planning", "experience_research")
        builder.add_edge(["stay_research", "mobility_research", "experience_research"], "research_barrier")
        builder.add_conditional_edges("research_barrier", route_after_research, {"continue": "candidate_merge", "error": END})
        builder.add_edge("candidate_merge", "recommendation_planner")
        builder.add_conditional_edges("recommendation_planner", route_after_planner, {"continue": "validate_candidates", "error": END})
        builder.add_conditional_edges("validate_candidates", route_after_validation, {"continue": "finalize_output", "error": END})
        builder.add_edge("finalize_output", END)
        return builder.compile()


def route_after_research(state: TripPlanningGraphState) -> str:
    return "error" if state.graph_error else "continue"


def route_from_start(state: TripPlanningGraphState) -> str:
    return "cross_day_replan" if state.mode == "cross_day_replan" else "initial_plan"


def route_after_planner(state: TripPlanningGraphState) -> str:
    return "error" if state.graph_error else "continue"


def route_after_validation(state: TripPlanningGraphState) -> str:
    return "error" if state.graph_error else "continue"


def skeleton_planning_update(state: TripPlanningGraphState) -> dict:
    next_state = skeleton_planning_node(state.model_copy(deep=True))
    return {
        "skeleton_plan": next_state.skeleton_plan,
        "trace": [next_state.trace[-1]],
    }


def stay_research_update(state: TripPlanningGraphState, provider) -> dict:
    next_state = stay_research_node(state.model_copy(deep=True), provider)
    update = {
        "stay_outcome": next_state.stay_outcome,
        "stay_result": next_state.stay_result,
        "trace": [next_state.trace[-1]],
    }
    if next_state.graph_error:
        update["graph_error"] = next_state.graph_error
    return update


def mobility_research_update(state: TripPlanningGraphState, provider) -> dict:
    next_state = mobility_research_node(state.model_copy(deep=True), provider)
    update = {
        "mobility_outcome": next_state.mobility_outcome,
        "mobility_result": next_state.mobility_result,
        "trace": [next_state.trace[-1]],
    }
    if next_state.graph_error:
        update["graph_error"] = next_state.graph_error
    return update


def experience_research_update(state: TripPlanningGraphState, provider) -> dict:
    next_state = experience_research_node(state.model_copy(deep=True), provider)
    update = {
        "experience_outcome": next_state.experience_outcome,
        "experience_result": next_state.experience_result,
        "trace": [next_state.trace[-1]],
    }
    if next_state.graph_error:
        update["graph_error"] = next_state.graph_error
    return update


def research_barrier_node(state: TripPlanningGraphState) -> dict:
    return {"trace": [{"node": "research_barrier_node", "status": "error" if state.graph_error else "success"}]}


def candidate_merge_update(state: TripPlanningGraphState) -> dict:
    next_state = candidate_merge_node(state.model_copy(deep=True))
    return {
        "candidate_context": next_state.candidate_context,
        "trace": [next_state.trace[-1]],
    }


def recommendation_planner_update(state: TripPlanningGraphState, provider) -> dict:
    next_state = recommendation_planner_node(state.model_copy(deep=True), provider)
    update = {
        "recommendations": next_state.recommendations,
        "trace": [next_state.trace[-1]],
    }
    if next_state.graph_error:
        update["graph_error"] = next_state.graph_error
    return update


def validate_candidates_update(state: TripPlanningGraphState) -> dict:
    next_state = validate_candidates_node(state.model_copy(deep=True))
    update = {
        "recommendations": next_state.recommendations,
        "validation_result": next_state.validation_result,
        "trace": [next_state.trace[-1]],
    }
    if next_state.graph_error:
        update["graph_error"] = next_state.graph_error
    return update


def get_affected_node_ids(intent: dict) -> list[str]:
    if intent.get("affected_node_ids"):
        return intent["affected_node_ids"]
    if intent.get("node_id"):
        return [intent["node_id"]]
    return []


def finalize_output_update(state: TripPlanningGraphState, provider) -> dict:
    next_state = finalize_output_node(state.model_copy(deep=True), provider=provider)
    update = {
        "final_recommendation_set": next_state.final_recommendation_set,
        "final_trip_proposal": next_state.final_trip_proposal,
        "status": next_state.status,
        "trace": [next_state.trace[-1]],
    }
    if next_state.graph_error:
        update["graph_error"] = next_state.graph_error
    return update
