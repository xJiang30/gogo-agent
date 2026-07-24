from typing import Any


class TripBoardBuilder:
    """Convert graph recommendations into the single Trip Board shown to users."""

    def build(self, *, recommendation_set: dict[str, Any]) -> dict[str, Any]:
        recommendations = recommendation_set.get("recommendations", [])
        if not recommendations:
            return {
                "trip": fallback_trip_board(recommendation_set),
                "source_recommendation": None,
                "source_recommendation_set": recommendation_set,
                "evidence": [],
                "warnings": ["No recommendation candidates were available; created a minimal board."],
            }

        recommendation = recommendations[0]
        return {
            "trip": recommendation_to_trip(recommendation),
            "source_recommendation": recommendation,
            "source_recommendation_set": recommendation_set,
            "evidence": recommendation.get("evidence", []),
            "warnings": recommendation.get("warnings", []),
        }


def recommendation_to_trip(recommendation: dict[str, Any]) -> dict[str, Any]:
    days = []
    for day_plan in recommendation.get("day_plans", []):
        day_number = day_plan.get("day") or len(days) + 1
        day_id = f"day-{day_number}"
        nodes = []
        for node_index, block in enumerate(day_plan.get("blocks", []), 1):
            nodes.append(
                {
                    "id": f"{day_id}-n{node_index}",
                    "type": block.get("type", "activity"),
                    "time": block.get("time_of_day", ""),
                    "title": block.get("title", "Untitled activity"),
                    "location": block.get("location"),
                    "duration": block.get("duration"),
                    "detail": block.get("rationale") or block.get("location") or "",
                    "booked": False,
                },
            )
        days.append(
            {
                "id": day_id,
                "title": day_plan.get("title", f"Day {day_number}"),
                "area": day_plan.get("area"),
                "pace": day_plan.get("pace"),
                "nodes": nodes,
            },
        )

    if not days:
        days = [
            {
                "id": "day-1",
                "title": recommendation.get("title", "Generated Trip Board"),
                "nodes": [
                    {
                        "id": "day-1-n1",
                        "type": "summary",
                        "title": recommendation.get("summary") or recommendation.get("theme") or "Review selected plan",
                        "detail": "Fallback node because the recommendation did not include day_plans.",
                        "booked": False,
                    },
                ],
            },
        ]

    return {
        "id": f"trip-{recommendation.get('id', 'board')}",
        "version": 1,
        "title": recommendation.get("title", "Generated Trip Board"),
        "source_recommendation_id": recommendation.get("id"),
        "days": days,
    }


def fallback_trip_board(recommendation_set: dict[str, Any]) -> dict[str, Any]:
    intent = recommendation_set.get("trip_intent", {})
    title = "Generated Trip Board"
    if intent.get("destination"):
        title = f"{intent['destination']} Trip Board"
    return {
        "id": "trip-board-fallback",
        "version": 1,
        "title": title,
        "days": [],
    }
