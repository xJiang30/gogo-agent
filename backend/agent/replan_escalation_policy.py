from backend.agent.contracts.routing_and_proposal import EscalationDecision


class ReplanEscalationPolicy:
    def decide(self, input_data: dict) -> dict:
        affected_day_ids = input_data.get("affected_day_ids", [])
        affected_node_ids = input_data.get("affected_node_ids", [])
        intent_kind = input_data.get("intent_kind", "ask")
        reasons = []

        if intent_kind == "initial_plan":
            return {
                "decision": EscalationDecision.GRAPH_REPLAN.value,
                "reasons": ["Initial planning requires graph orchestration"],
                "affected_day_ids": affected_day_ids,
                "affected_node_ids": affected_node_ids,
            }

        if len(affected_day_ids) >= 2:
            reasons.append("Touches multiple days")
        if input_data.get("requires_stay_reorder"):
            reasons.append("Requires stay-anchor reorder")
        if input_data.get("requires_cross_city_rebuild"):
            reasons.append("Requires cross-city mobility rebuild")
        if input_data.get("breaks_multi_day_constraints"):
            reasons.append("Breaks multi-day constraints")

        if reasons or input_data.get("can_close_locally") is False:
            return {
                "decision": EscalationDecision.GRAPH_REPLAN.value,
                "reasons": reasons,
                "affected_day_ids": affected_day_ids,
                "affected_node_ids": affected_node_ids,
            }

        if intent_kind == "replace":
            return {
                "decision": EscalationDecision.LIGHTWEIGHT_RESEARCH.value,
                "reasons": ["Single-node free text is consultative unless explicit replan is requested"],
                "affected_day_ids": affected_day_ids,
                "affected_node_ids": affected_node_ids,
            }

        if intent_kind == "research":
            return {
                "decision": EscalationDecision.LIGHTWEIGHT_RESEARCH.value,
                "reasons": ["Needs provider lookup but not replanning"],
                "affected_day_ids": affected_day_ids,
                "affected_node_ids": affected_node_ids,
            }

        return {
            "decision": EscalationDecision.DIRECT_ANSWER.value,
            "reasons": ["Can answer directly without proposal"],
            "affected_day_ids": affected_day_ids,
            "affected_node_ids": affected_node_ids,
        }
