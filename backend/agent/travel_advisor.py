from backend.agent.clarification_policy import ClarificationPolicy
from backend.agent.graph import TripPlanningGraph
from backend.agent.lightweight_flows import LightweightFlows
from backend.agent.planning_brief_builder import PlanningBriefBuilder
from backend.agent.contracts.planning import PlanningBrief
from backend.agent.contracts.replan_routing import ReplanNeed, SpecialistSelection
from backend.agent.proposal_executor import ProposalExecutor
from backend.agent.proposal_service import ProposalService
from backend.agent.providers.errors import LlmProviderError
from backend.agent.providers.failure_policy import classify_provider_failure
from backend.agent.replan_escalation_policy import ReplanEscalationPolicy
from backend.agent.replan_intent_router import ReplanIntentRouter
from backend.agent.specialist_selector import SpecialistSelector
from backend.agent.trip_board_builder import TripBoardBuilder


class TravelAdvisor:
    """User-facing orchestration layer above TripPlanningGraph."""

    def __init__(
        self,
        *,
        graph: TripPlanningGraph | None = None,
        proposal_service: ProposalService | None = None,
        executor: ProposalExecutor | None = None,
        lightweight_flows: LightweightFlows | None = None,
        escalation_policy: ReplanEscalationPolicy | None = None,
        planning_brief_builder: PlanningBriefBuilder | None = None,
        replan_intent_router: ReplanIntentRouter | None = None,
        specialist_selector: SpecialistSelector | None = None,
        clarification_policy: ClarificationPolicy | None = None,
        trip_board_builder: TripBoardBuilder | None = None,
    ) -> None:
        self.graph = graph or TripPlanningGraph()
        self.proposal_service = proposal_service or ProposalService()
        self.executor = executor or ProposalExecutor()
        self.lightweight_flows = lightweight_flows or LightweightFlows(provider=getattr(self.graph, "provider", None))
        self.escalation_policy = escalation_policy or ReplanEscalationPolicy()
        self.replan_intent_router = replan_intent_router or ReplanIntentRouter(provider=getattr(self.graph, "provider", None))
        self.specialist_selector = specialist_selector or SpecialistSelector(provider=getattr(self.graph, "provider", None))
        self.clarification_policy = clarification_policy or ClarificationPolicy(provider=getattr(self.graph, "provider", None))
        self.trip_board_builder = trip_board_builder or TripBoardBuilder()
        self.planning_brief_builder = planning_brief_builder or getattr(
            self.graph,
            "planning_brief_builder",
            PlanningBriefBuilder(provider=getattr(self.graph, "provider", None)),
        )

    def handle_request(
        self,
        *,
        user_id: str,
        conversation_id: str,
        user_message: str,
        trip: dict | None = None,
        intent: dict | None = None,
    ) -> dict:
        intent = normalize_intent(intent, trip)
        requested_mode = intent.get("mode") or intent.get("action")
        if requested_mode == "initial_plan":
            intent["kind"] = "initial_plan"
            intent["can_close_locally"] = False

        clarification = self.clarification_policy.decide(user_message=user_message, trip=trip, intent=intent)
        if clarification.should_ask:
            planning_brief = PlanningBrief(mode="clarification", origin_message=user_message)
            return clarification_response(clarification, planning_brief)

        routing = self.build_routing(user_message=user_message, trip=trip, intent=intent)
        planning_brief = response_planning_brief(
            user_message=user_message,
            intent=intent,
            routing=routing,
            builder=self.planning_brief_builder,
        )

        request = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "user_message": user_message,
            "trip": trip,
            "intent": intent,
            "routing": routing,
        }

        if routing["decision"] == "direct_answer":
            try:
                answer = self.lightweight_flows.answer(request)
                return answer_response(routing, planning_brief, answer["text"])
            except Exception as error:
                fallback = decide_lightweight_fallback(error)
                return answer_response(routing, planning_brief, fallback["message"], fallback=fallback)

        if routing["decision"] == "lightweight_research":
            try:
                answer = self.lightweight_flows.research(request)
                return answer_response(routing, planning_brief, answer["text"])
            except Exception as error:
                fallback = decide_lightweight_fallback(error)
                return answer_response(routing, planning_brief, fallback["message"], fallback=fallback)

        proposal_id = f"{routing['decision']}-manual"
        if routing["decision"] == "local_proposal":
            if not trip or not intent.get("node_id"):
                fallback = missing_local_proposal_context_fallback(trip=trip, intent=intent)
                return answer_response(routing, planning_brief, fallback["message"], fallback=fallback)
            try:
                result = self.lightweight_flows.local_proposal({**request, "proposal_id": proposal_id})
            except LlmProviderError as error:
                fallback = local_proposal_provider_fallback(error)
                return answer_response(routing, planning_brief, fallback["message"], fallback=fallback)
            except ValueError as error:
                fallback = local_proposal_error_fallback(error)
                return answer_response(routing, planning_brief, fallback["message"], fallback=fallback)
            stored = self.proposal_service.persist_proposal(
                result["proposal"],
                current_trip_version=trip["version"],
            )
            return proposal_response(routing, planning_brief, stored)

        if routing["decision"] == "regenerate_recommendations":
            graph_result = self.graph.run_initial_plan(user_message, user_id=user_id, planning_brief=planning_brief)
        elif intent.get("kind") == "initial_plan" or requested_mode == "initial_plan":
            graph_result = self.graph.run_initial_plan(user_message, user_id=user_id, planning_brief=planning_brief)
        elif trip:
            graph_result = self.graph.run_replan(
                user_message=user_message,
                trip=trip,
                intent=intent,
                user_id=user_id,
                proposal_id=proposal_id,
            )
        else:
            graph_result = self.graph.run_initial_plan(user_message, user_id=user_id)
        if graph_result["kind"] == "graph_error":
            fallback = decide_advisor_fallback(intent=intent, graph_error=graph_result["graphError"])
            return answer_response(routing, planning_brief, fallback["message"], fallback=fallback)

        if graph_result["kind"] == "proposal":
            stored = self.proposal_service.persist_proposal(
                graph_result["proposal"],
                current_trip_version=trip["version"],
            )
            return proposal_response(routing, planning_brief, stored)

        if graph_result["kind"] == "recommendation_set":
            return trip_board_response(
                routing=routing,
                planning_brief=planning_brief,
                graph_result=graph_result,
                builder=self.trip_board_builder,
                conversation_id=conversation_id,
            )

        graph_result["routing"] = routing
        graph_result["planningBrief"] = planning_brief.model_dump()
        graph_result["conversationId"] = conversation_id
        return graph_result

    def execute_proposal(self, *, trip: dict, proposal_id: str) -> dict:
        proposal = self.proposal_service.get_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")
        return execution_response(self.executor.execute(trip, proposal))

    def build_routing(self, *, user_message: str, trip: dict | None, intent: dict) -> dict:
        decision = self.replan_intent_router.classify(user_message=user_message, trip=trip, intent=intent)
        decision = enforce_trip_board_edit_policy(decision, intent=intent)
        specialist_selection = self.specialist_selector.select(user_message=user_message, intent=intent)
        specialist_selection = add_default_node_specialist(
            specialist_selection,
            trip=trip,
            node_id=intent.get("node_id") or first_or_none(decision.affected_node_ids),
        )
        return {
            "decision": decision.decision,
            "reasons": decision.reasons,
            "affected_day_ids": decision.affected_day_ids,
            "affected_node_ids": decision.affected_node_ids,
            "replan": decision.model_dump(mode="json"),
            "specialistSelection": specialist_selection.model_dump(mode="json"),
        }


def normalize_intent(intent: dict | None, trip: dict | None) -> dict:
    if intent:
        return normalize_intent_keys(intent)
    return {
        "kind": "initial_plan" if not trip else "ask",
        "scope": "trip",
        "affected_day_ids": [],
        "can_close_locally": False if not trip else True,
    }


def response_planning_brief(*, user_message: str, intent: dict, routing: dict, builder: PlanningBriefBuilder) -> PlanningBrief:
    if intent.get("kind") == "initial_plan" or intent.get("mode") == "initial_plan" or intent.get("action") == "initial_plan":
        return builder.build_initial_planning_brief(user_message)
    if routing["decision"] == "regenerate_recommendations":
        return PlanningBrief(mode="regenerate_recommendations", origin_message=user_message)
    if routing["decision"] == "local_proposal":
        return PlanningBrief(mode="local_proposal", origin_message=user_message)
    if routing["decision"] == "graph_replan":
        return PlanningBrief(
            mode=routing.get("replan", {}).get("scope", "cross_day_replan"),
            origin_message=user_message,
            affected_day_ids=intent.get("affected_day_ids", []),
            affected_node_ids=get_affected_node_ids(intent),
        )
    return PlanningBrief(mode="discussion_turn", origin_message=user_message)


def enforce_trip_board_edit_policy(decision, *, intent: dict):
    explicit_edit = normalize_intent_kind(intent.get("kind")) == "replan"
    requested_mode = intent.get("mode") or intent.get("action")
    if requested_mode in {"replan", "day_replan", "cross_day_replan", "full_replan", "regenerate_recommendations"}:
        explicit_edit = True
    if decision.decision == "local_proposal" and not explicit_edit:
        decision.scope = "lightweight_research"
        decision.decision = "lightweight_research"
        decision.output_kind = "answer"
        decision.reasons = [
            *decision.reasons,
            "Trip Board free text is consultative; only explicit replan actions can mutate the trip",
        ]
    return decision


def add_default_node_specialist(selection: SpecialistSelection, *, trip: dict | None, node_id: str | None) -> SpecialistSelection:
    node = find_trip_node(trip, node_id) if trip and node_id else None
    need = default_need_for_node(node)
    if not need or need in selection.needs:
        return selection
    return SpecialistSelection(
        needs=[*selection.needs, need],
        reasons=[*selection.reasons, f"Target node type defaults to {need.value} specialist"],
    )


def default_need_for_node(node: dict | None) -> ReplanNeed | None:
    if not node:
        return None
    node_type = str(node.get("type", "")).lower()
    if node_type in {"hotel", "stay", "lodging", "accommodation"}:
        return ReplanNeed.STAY
    if node_type in {"transport", "mobility", "transfer", "route", "flight", "rail"}:
        return ReplanNeed.MOBILITY
    if node_type in {"food", "meal", "restaurant", "activity", "attraction", "experience"}:
        return ReplanNeed.EXPERIENCE
    return None


def find_trip_node(trip: dict | None, node_id: str | None) -> dict | None:
    if not trip or not node_id:
        return None
    for day in trip.get("days", []):
        for node in day.get("nodes", []):
            if node.get("id") == node_id:
                return node
    return None


def first_or_none(values: list[str]) -> str | None:
    return values[0] if values else None


def normalize_intent_keys(intent: dict) -> dict:
    normalized = dict(intent)
    alias_map = {
        "affectedDayIds": "affected_day_ids",
        "affectedNodeIds": "affected_node_ids",
        "nodeId": "node_id",
        "replacementType": "replacement_type",
        "requiresStayReorder": "requires_stay_reorder",
        "requiresCrossCityRebuild": "requires_cross_city_rebuild",
        "canCloseLocally": "can_close_locally",
        "breaksMultiDayConstraints": "breaks_multi_day_constraints",
    }
    for frontend_key, backend_key in alias_map.items():
        if frontend_key in normalized and backend_key not in normalized:
            normalized[backend_key] = normalized[frontend_key]
    return normalized


def normalize_intent_kind(kind: str | None) -> str:
    if kind in {"replace_hotel", "replace_node", "replace_transport"}:
        return "replace"
    if kind in {"day_replan", "cross_day_replan", "full_replan", "all_replan"}:
        return "replan"
    if kind in {"initial_plan", "replace", "research", "replan", "regenerate_recommendations"}:
        return kind
    return "ask"


def get_affected_node_ids(intent: dict) -> list[str]:
    if intent.get("affected_node_ids"):
        return intent["affected_node_ids"]
    if intent.get("node_id"):
        return [intent["node_id"]]
    return []


def decide_advisor_fallback(*, intent: dict, graph_error: dict) -> dict:
    if graph_error["decision"] == "retry_later" and intent.get("kind") == "replan":
        return {
            "layer": "advisor",
            "decision": "ask_retry_later",
            "message": "The planning graph could not finish reliably. Please retry later.",
            "source": "graph",
            "retryable": True,
            "graph_error": graph_error,
        }

    if graph_error["decision"] == "retry_later":
        return {
            "layer": "advisor",
            "decision": "fallback_to_answer",
            "message": "The graph timed out, so returning a safe explanatory answer instead.",
            "source": "graph",
            "retryable": True,
            "graph_error": graph_error,
        }

    return {
        "layer": "advisor",
        "decision": "surface_error",
        "message": "The graph failed in a way that should be surfaced to the caller.",
        "source": "graph",
        "retryable": False,
        "graph_error": graph_error,
    }


def missing_local_proposal_context_fallback(*, trip: dict | None, intent: dict) -> dict:
    missing = []
    if not trip:
        missing.append("trip")
    if not intent.get("node_id"):
        missing.append("node_id")
    return {
        "layer": "advisor",
        "decision": "missing_trip_for_local_proposal" if "trip" in missing else "missing_node_for_local_proposal",
        "message": "这次替换需要当前行程和节点信息。请先选择一个行程节点，再让我生成替换提案。",
        "source": "advisor",
        "retryable": False,
        "missing": missing,
    }


def local_proposal_error_fallback(error: ValueError) -> dict:
    return {
        "layer": "advisor",
        "decision": "local_proposal_node_not_found",
        "message": "我没有在当前行程里找到这个节点。请重新选择要替换的节点。",
        "source": "advisor",
        "retryable": False,
        "error": str(error),
    }


def local_proposal_provider_fallback(error: LlmProviderError) -> dict:
    return {
        "layer": "advisor",
        "decision": "local_proposal_provider_failed",
        "message": "这次替换提案没有生成成功。请重新试一次，或补充你想替换成什么类型。",
        "source": "lightweight",
        "retryable": error.retryable,
        "error_code": error.code,
        "reason": str(error),
    }


def decide_lightweight_fallback(error: Exception) -> dict:
    failure = classify_provider_failure(error)
    return {
        "layer": "advisor",
        "decision": "fallback_to_answer",
        "message": "这次轻量回答没有成功。你可以重新试一次，或者让我进入完整规划模式处理。",
        "source": "lightweight",
        "retryable": failure["retryable"],
        "error_code": failure["error_code"],
        "reason": failure["reason"],
    }


def answer_response(routing: dict, planning_brief, text: str, fallback: dict | None = None) -> dict:
    return {
        "kind": "answer",
        "routing": routing,
        "planningBrief": planning_brief.model_dump(),
        "text": text,
        "fallback": fallback,
    }


def clarification_response(clarification, planning_brief) -> dict:
    questions = [question.model_dump() for question in clarification.questions]
    return {
        "kind": "clarification_question",
        "routing": {
            "decision": "clarification_question",
            "reasons": [clarification.reason] if clarification.reason else [],
        },
        "planningBrief": planning_brief.model_dump(),
        "questions": questions,
        "text": questions[0]["text"] if questions else "我需要先确认几个信息，才能开始规划。",
        "reason": clarification.reason,
    }


def trip_board_response(*, routing: dict, planning_brief, graph_result: dict, builder: TripBoardBuilder, conversation_id: str) -> dict:
    built = builder.build(recommendation_set=graph_result["recommendationSet"])
    return {
        "kind": "trip_board",
        "routing": routing,
        "planningBrief": planning_brief.model_dump(),
        "trip": built["trip"],
        "sourceRecommendation": built["source_recommendation"],
        "sourceRecommendationSet": built["source_recommendation_set"],
        "evidence": built["evidence"],
        "warnings": built["warnings"],
        "trace": graph_result.get("trace", []),
        "conversationId": conversation_id,
    }


def proposal_response(routing: dict, planning_brief, proposal) -> dict:
    proposal_payload = proposal.model_dump()
    return {
        "kind": "proposal",
        "routing": routing,
        "planningBrief": planning_brief.model_dump(),
        "proposal": proposal_payload,
        "frontendProposal": to_camel_case_contract(proposal_payload),
    }


def execution_response(execution: dict) -> dict:
    return {
        "kind": "execution",
        **execution,
    }


def to_camel_case_contract(value):
    if isinstance(value, list):
        return [to_camel_case_contract(item) for item in value]
    if isinstance(value, dict):
        return {snake_to_camel(key): to_camel_case_contract(item) for key, item in value.items()}
    return value


def snake_to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])
