import argparse
from dataclasses import dataclass, field
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.agent.travel_advisor import TravelAdvisor


LAST_OUTPUT_PATH = PROJECT_ROOT / "manual-agent-last-output.json"


class BackToMenu(Exception):
    """Raised when the tester wants to leave the current prompt without running it."""


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    load_dotenv(PROJECT_ROOT / ".env")
    if args.self_check:
        print_self_check()
        return

    advisor = TravelAdvisor()
    run_manual_rounds(advisor)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manual E2E playground for the real Python Gogo agent.")
    parser.add_argument("--self-check", action="store_true", help="Check startup and .env visibility without calling the model.")
    return parser.parse_args()


def print_self_check() -> None:
    visible = {
        "LLM_API_BASE": bool(os.getenv("LLM_API_BASE")),
        "LLM_API_KEY": bool(os.getenv("LLM_API_KEY")),
        "LLM_MODEL_NAME": bool(os.getenv("LLM_MODEL_NAME")),
    }
    print("Self-check OK. No model call was made.")
    print(json.dumps(visible, ensure_ascii=False, indent=2))


@dataclass
class ManualTestSession:
    current_trip: dict | None = None
    history: list[dict] = field(default_factory=list)
    latest_recommendation_set: dict | None = None
    latest_proposal_id: str | None = None


def run_manual_rounds(advisor: TravelAdvisor) -> None:
    session = ManualTestSession()
    print("Gogo Agent Five-Round Manual Test")
    print("---------------------------------")
    print("This uses the real model from .env.")
    print("Follow the prompts. Press Enter to use each suggested test input.")

    try:
        print_round_header(1, "初始规划", "OK: 有 3 个方案，包含住宿/周边游/美食，不完全重复。")
        result = run_round_initial_plan(
            advisor,
            session,
            input_or_default("Travel request", "帮我规划一个福冈三日游，想吃好吃的，也想安排一天周边游，节奏不要太赶"),
        )
        print_result(result)
        save_last_output(result)

        print_round_header(2, "上下文追问", "OK: 能基于上一轮方案回答第二天是否太赶，而不是要求你重新提供行程。")
        result = run_round_context_followup(
            advisor,
            session,
            input_or_default("Follow-up question", "你觉得第二天会不会太赶？"),
        )
        print_result(result)
        save_last_output(result)

        print_round_header(3, "Show generated Trip Board", "OK: Round 1 already created current_trip; this round displays Day/Node for manual inspection.")
        if session.current_trip:
            print_trip_nodes(session.current_trip)
        else:
            print("No current Trip Board was generated in Round 1.")

        print_round_header(4, "生成修改 Proposal", "OK: 返回 kind=proposal，有 proposal_id 和 operations，不直接改 trip。")
        result = run_round_proposal(
            advisor,
            session,
            input_or_default("Modification request", "第二天和第三天都有点赶，帮我重新平衡一下，但不要减少美食"),
        )
        print_result(result)
        save_last_output(result)

        print_round_header(5, "接受并执行 Proposal", "OK: 返回 kind=execution，trip version 增加，并记录 proposal id。")
        confirmation = input_or_default("Accept latest proposal?", "接受这个修改")
        if looks_like_acceptance(confirmation):
            result = run_round_accept(advisor, session)
        else:
            result = {"kind": "manual_skipped", "message": "Round 5 skipped because the proposal was not accepted."}
        print_result(result)
        save_last_output(result)
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting manual playground.")
    except BackToMenu:
        print("\nStopped. Exiting manual playground.")


def print_round_header(number: int, title: str, ok_standard: str) -> None:
    print(f"\nRound {number}. {title}")
    print("-" * 40)
    print(ok_standard)


def run_round_initial_plan(advisor: TravelAdvisor, session: ManualTestSession, message: str) -> dict:
    result = advisor.handle_request(
        user_id="manual-user",
        conversation_id="manual-five-rounds",
        user_message=message,
        trip=None,
        intent={"kind": "initial_plan", "mode": "initial_plan", "can_close_locally": False},
    )
    update_manual_session(session, message, result)
    return result


def run_round_context_followup(advisor: TravelAdvisor, session: ManualTestSession, message: str) -> dict:
    user_message = build_context_message(
        message=message,
        history=session.history,
        current_trip=session.current_trip,
        latest_recommendation_set=session.latest_recommendation_set,
    )
    result = advisor.handle_request(
        user_id="manual-user",
        conversation_id="manual-five-rounds",
        user_message=user_message,
        trip=session.current_trip,
        intent={"kind": "ask", "scope": "trip", "affected_day_ids": [], "can_close_locally": True},
    )
    update_manual_session(session, message, result)
    return result


def select_recommendation_as_current_trip(session: ManualTestSession, selection: int) -> dict:
    recommendation_set = session.latest_recommendation_set or {}
    recommendations = recommendation_set.get("recommendations", [])
    if not recommendations:
        raise ValueError("No recommendation set is available. Finish Round 1 first.")
    index = max(1, min(selection, len(recommendations))) - 1
    trip = recommendation_to_trip(recommendations[index], index=index)
    session.current_trip = trip
    return trip


def run_round_proposal(advisor: TravelAdvisor, session: ManualTestSession, message: str) -> dict:
    if not session.current_trip:
        raise ValueError("No current trip is available. Finish Round 3 first.")
    intent = build_replan_intent(message, session.current_trip)
    result = advisor.handle_request(
        user_id="manual-user",
        conversation_id="manual-five-rounds",
        user_message=build_context_message(
            message=message,
            history=session.history,
            current_trip=session.current_trip,
            latest_recommendation_set=session.latest_recommendation_set,
        ),
        trip=session.current_trip,
        intent=intent,
    )
    update_manual_session(session, message, result)
    return result


def run_round_accept(advisor: TravelAdvisor, session: ManualTestSession) -> dict:
    if not session.current_trip:
        return {"kind": "manual_error", "message": "No current trip is available. Finish Round 3 first."}
    if not session.latest_proposal_id:
        return {"kind": "manual_error", "message": "No proposal is available. Finish Round 4 first."}
    if hasattr(advisor, "proposal_service"):
        accepted = advisor.proposal_service.update_proposal_status(session.latest_proposal_id, "accepted")
        if not accepted:
            return {
                "kind": "manual_error",
                "message": f"Proposal {session.latest_proposal_id} could not be accepted.",
            }
    result = advisor.execute_proposal(trip=session.current_trip, proposal_id=session.latest_proposal_id)
    if result.get("kind") == "execution":
        session.current_trip = result["trip"]
    return result


def build_context_message(
    *,
    message: str,
    history: list[dict],
    current_trip: dict | None,
    latest_recommendation_set: dict | None,
) -> str:
    sections = [f"User message:\n{message}"]
    if history:
        sections.append("Conversation history:\n" + summarize_history(history))
    if latest_recommendation_set:
        sections.append("Latest recommendation summary:\n" + summarize_recommendation_set(latest_recommendation_set))
    if current_trip:
        sections.append("Current trip summary:\n" + summarize_trip(current_trip))
    return "\n\n".join(sections)


def summarize_history(history: list[dict], limit: int = 6) -> str:
    recent = history[-limit:]
    lines = []
    for item in recent:
        role = item.get("role", "message")
        content = str(item.get("content", "")).strip()
        if len(content) > 500:
            content = content[:497] + "..."
        lines.append(f"- {role}: {content}")
    return "\n".join(lines)


def summarize_recommendation_set(recommendation_set: dict) -> str:
    recommendations = recommendation_set.get("recommendations", [])
    lines = []
    for index, item in enumerate(recommendations[:3], 1):
        title = item.get("title", f"Plan {index}")
        summary = item.get("summary") or item.get("theme") or ""
        lines.append(f"- Option {index}: {title}. {summary}")
    return "\n".join(lines) or "No recommendation options were saved yet."


def summarize_trip(trip: dict) -> str:
    lines = [f"trip_id: {trip.get('id')}", f"version: {trip.get('version')}"]
    for day in trip.get("days", []):
        lines.append(f"{day.get('id')} - {day.get('title')}")
        for node in day.get("nodes", []):
            node_parts = [
                node.get("id", "node"),
                node.get("type", "item"),
                node.get("time", ""),
                node.get("title", ""),
                node.get("detail", ""),
            ]
            lines.append("  - " + " | ".join(str(part) for part in node_parts if part))
    return "\n".join(lines)


def update_manual_session(session: ManualTestSession, message: str, result: dict) -> None:
    session.history.append({"role": "user", "content": message})
    if result.get("kind") == "trip_board":
        session.current_trip = result.get("trip")
        session.latest_recommendation_set = result.get("sourceRecommendationSet")
    if result.get("kind") == "recommendation_set":
        session.latest_recommendation_set = result.get("recommendationSet")
    if result.get("kind") == "proposal":
        proposal = result.get("proposal", {})
        session.latest_proposal_id = proposal.get("proposal_id")
    session.history.append({"role": "assistant", "content": summarize_result_for_history(result)})


def recommendation_to_trip(recommendation: dict, *, index: int = 0) -> dict:
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
        days = fallback_trip_days(recommendation)
    return {
        "id": f"manual-trip-{recommendation.get('id', index + 1)}",
        "version": 1,
        "title": recommendation.get("title", "Selected recommendation"),
        "source_recommendation_id": recommendation.get("id"),
        "days": days,
    }


def fallback_trip_days(recommendation: dict) -> list[dict]:
    return [
        {
            "id": "day-1",
            "title": recommendation.get("title", "Selected recommendation"),
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


def build_replan_intent(message: str, trip: dict) -> dict:
    affected_day_ids = infer_affected_day_ids(message, trip)
    affected_node_ids = [
        node["id"]
        for day in trip.get("days", [])
        if day.get("id") in affected_day_ids
        for node in day.get("nodes", [])
        if node.get("id")
    ]
    return {
        "kind": "replan",
        "scope": "trip",
        "affected_day_ids": affected_day_ids,
        "affected_node_ids": affected_node_ids,
        "can_close_locally": False,
        "breaks_multi_day_constraints": True,
    }


def infer_affected_day_ids(message: str, trip: dict) -> list[str]:
    mapping = [
        ("第一天", "day-1"),
        ("第1天", "day-1"),
        ("第二天", "day-2"),
        ("第2天", "day-2"),
        ("第三天", "day-3"),
        ("第3天", "day-3"),
    ]
    day_ids = [day_id for token, day_id in mapping if token in message]
    valid_day_ids = {day.get("id") for day in trip.get("days", [])}
    filtered = [day_id for day_id in day_ids if day_id in valid_day_ids]
    if filtered:
        return filtered
    return [trip["days"][0]["id"]] if trip.get("days") else []


def print_recommendation_options(recommendation_set: dict | None) -> None:
    recommendations = (recommendation_set or {}).get("recommendations", [])
    if not recommendations:
        print("No recommendations available.")
        return
    for index, item in enumerate(recommendations, 1):
        print(f"{index}. {item.get('title', f'Plan {index}')}")


def parse_selection(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 1


def looks_like_acceptance(message: str) -> bool:
    lowered = message.lower()
    return any(token in message for token in ["接受", "确认", "同意", "执行"]) or "accept" in lowered


def summarize_result_for_history(result: dict) -> str:
    if result.get("kind") == "answer":
        return result.get("text", "")
    if result.get("kind") == "trip_board":
        trip = result.get("trip", {})
        return f"Trip Board {trip.get('id')}: {trip.get('title')}"
    if result.get("kind") == "recommendation_set":
        return summarize_recommendation_set(result.get("recommendationSet", {}))
    if result.get("kind") == "proposal":
        proposal = result.get("proposal", {})
        return f"Proposal {proposal.get('proposal_id')}: {proposal.get('title')}"
    return json.dumps(result, ensure_ascii=False)[:1000]


def print_result(result: dict) -> None:
    print("\nResult")
    print("--------------------------------")
    print(f"kind: {result.get('kind')}")
    if result.get("routing"):
        print(f"routing: {result['routing'].get('decision')}")
    if result.get("kind") == "answer":
        print(result.get("text", ""))
        if result.get("fallback"):
            print("\nfallback:")
            print(json.dumps(result["fallback"], ensure_ascii=False, indent=2))
    elif result.get("kind") == "recommendation_set":
        recommendations = result["recommendationSet"]["recommendations"]
        print(f"recommendations: {len(recommendations)}")
        for item in recommendations:
            print(f"- {item['title']} ({item['theme']})")
    elif result.get("kind") == "trip_board":
        trip = result["trip"]
        print(f"trip_id: {trip.get('id')}")
        print(f"title: {trip.get('title')}")
        print(f"days: {len(trip.get('days', []))}")
        if result.get("sourceRecommendation"):
            print(f"source recommendation: {result['sourceRecommendation'].get('title')}")
    elif result.get("kind") == "proposal":
        proposal = result["proposal"]
        print(f"proposal_id: {proposal['proposal_id']}")
        print(f"status: {proposal['status']}")
        print(f"title: {proposal['title']}")
        print(f"operations: {len(proposal['operations'])}")
    elif result.get("kind") == "execution":
        print(f"trip version: {result['trip']['version']}")
        print(f"executed proposal: {result['decisionLog']['proposalId']}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\nFull JSON saved to: {LAST_OUTPUT_PATH}")


def save_last_output(result: dict) -> None:
    LAST_OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


def input_or_default(label: str, default: str) -> str:
    print(f"\n{label}")
    print(f"Default: {default}")
    print("Press Enter to use default. Type b/back to stop this test.")
    value = input("> ").strip()
    if value.lower() in {"b", "back"}:
        raise BackToMenu()
    return value or default


def print_trip_nodes(trip: dict) -> None:
    print("\nSample trip nodes")
    for day in trip["days"]:
        print(f"{day['id']} - {day['title']}")
        for node in day["nodes"]:
            print(f"  {node['id']}: {node['type']} - {node['title']}")


def sample_trip() -> dict:
    return {
        "id": "trip-manual",
        "version": 1,
        "days": [
            {
                "id": "day-1",
                "title": "抵达福冈",
                "nodes": [
                    {"id": "n1", "type": "transport", "time": "14:00", "title": "抵达福冈机场", "detail": "入境后前往博多。"},
                    {"id": "n2", "type": "hotel", "time": "16:00", "title": "博多站酒店入住", "detail": "交通方便。"},
                    {"id": "n3", "type": "meal", "time": "19:00", "title": "天神拉面晚餐", "detail": "轻松晚餐。"},
                ],
            },
            {
                "id": "day-2",
                "title": "福冈城市探索",
                "nodes": [
                    {"id": "n4", "type": "place", "time": "10:00", "title": "大濠公园散步", "detail": "轻量开场。"},
                    {"id": "n5", "type": "place", "time": "14:00", "title": "博多老街区散步", "detail": "适合慢节奏探索。"},
                ],
            },
            {
                "id": "day-3",
                "title": "由布院周边游",
                "nodes": [
                    {"id": "n6", "type": "transport", "time": "09:00", "title": "由布院之森列车", "detail": "需要提前确认车次。"},
                    {"id": "n7", "type": "place", "time": "12:00", "title": "金鳞湖散步", "detail": "下午集中完成。"},
                ],
            },
        ],
    }


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


if __name__ == "__main__":
    main()
