from backend.agent.contracts.graph_state import TripPlanningGraphState


def candidate_merge_node(state: TripPlanningGraphState) -> TripPlanningGraphState:
    """Normalize specialist outputs into planner-ready candidate context."""
    state.candidate_context = {
        "stay_candidates": state.stay_result.model_dump() if state.stay_result else None,
        "mobility_candidates": state.mobility_result.model_dump() if state.mobility_result else None,
        "experience_candidates": state.experience_result.model_dump() if state.experience_result else None,
        "constraints": state.planning_brief.hard_constraints,
        "preferences": state.planning_brief.soft_preferences,
    }
    state.trace.append({"node": "candidate_merge_node"})
    return state
