from backend.agent.contracts.graph_state import TripPlanningGraphState


def skeleton_planning_node(state: TripPlanningGraphState) -> TripPlanningGraphState:
    duration = state.planning_brief.duration_days
    state.skeleton_plan = {
        "trip_shape": "multi-option discovery" if state.mode == "initial_plan" else "cross-day rebalance",
        "stay_strategy": "derive accommodation anchors from the planning brief and stay research",
        "mobility_strategy": "derive transport and day-trip feasibility from mobility research",
        "experience_strategy": "derive food, activities, and pacing from experience research",
        "day_frames": [{"day": day, "theme": f"day-{day}"} for day in range(1, duration + 1)] if duration else [],
    }
    state.trace.append({"node": "skeleton_planning_node"})
    return state
