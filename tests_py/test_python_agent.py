import io
import json
import unittest
from collections import Counter
from unittest.mock import patch

import manual_agent_playground
from backend.agent.contracts.advisor_io import ClarificationQuestionResponse, ProposalResponse
from backend.agent.contracts.errors import AdvisorFallbackDecision
from backend.agent.contracts.replan_routing import ReplanNeed, ReplanScope
from backend.agent.contracts.planning import PlanningBrief, TripPlanningGraphRequest
from backend.agent.planning_brief_builder import PlanningBriefBuilder
from backend.agent.contracts.routing_and_proposal import TripProposal
from backend.agent.contracts.research import ResearchResult
from backend.agent.graph import TripPlanningGraph
from backend.agent.clarification_policy import ClarificationPolicy
from backend.agent.providers.errors import LlmProviderError
from backend.agent.providers.qwen_provider import QwenResearchProvider
from backend.agent.proposal_executor import ProposalExecutor
from backend.agent.proposal_service import ProposalService
from backend.agent.specialist_selector import SpecialistSelector
from backend.agent.travel_advisor import TravelAdvisor
from backend.agent.nodes.recommendation_planner_node import parse_recommendations
from backend.application.agent_application_services import AgentApplicationServices


class FakeProvider:
    def generate_clarification_decision(self, *, system_prompt, user_prompt):
        return {
            "should_ask": False,
            "questions": [],
            "reason": "Test provider treats this request as sufficiently specified.",
        }

    def generate_research(self, *, domain, system_prompt, user_prompt):
        options = {
            "stay": [{"id": "stay-1", "label": "Hakata Station anchor", "rationale": "Easy transit."}],
            "mobility": [
                {
                    "id": "mobility-1",
                    "label": "Dazaifu day trip",
                    "transport": "train",
                    "transferPressure": "low",
                },
            ],
            "experience": [{"id": "exp-1", "name": "Yatai and ramen evening"}],
        }
        return {
            "summary": f"{domain} summary",
            "options": options[domain],
            "warnings": [],
            "missingInfo": ["dates"],
            "evidence": [f"{domain} evidence"],
            "assumptions": [],
            "confidence": 0.8,
        }

    def generate_recommendations(self, *, system_prompt, user_prompt):
        return {
            "recommendations": [
                fake_recommendation(
                    "plan-1",
                    "Hakata Station anchor base with Dazaifu day trip",
                    "Hakata Station anchor",
                    "Dazaifu",
                    ["Yatai and ramen evening"],
                    2.4,
                ),
                fake_recommendation(
                    "plan-2",
                    "Tenjin food base with Yanagawa day trip",
                    "Tenjin",
                    "Yanagawa",
                    ["Canal town snack walk"],
                    2.2,
                ),
                fake_recommendation(
                    "plan-3",
                    "Hakata transit-easy food plan",
                    "Hakata",
                    "Dazaifu",
                    ["Market breakfast"],
                    2.1,
                ),
            ],
        }

    def generate_replan_proposal(self, *, system_prompt, user_prompt):
        payload = json.loads(user_prompt)
        target_nodes = payload.get("targetNodes", [])
        operations = []
        for item in target_nodes:
            day_id = item.get("dayId")
            node = item.get("node", {})
            operations.append(
                {
                    "type": "UpdateNode",
                    "day_id": day_id,
                    "node_id": node.get("id"),
                    "patch": {
                        "title": f"Adjusted {node.get('title', 'trip item')}",
                        "detail": "Move this item into a calmer sequence and keep a nearby meal buffer.",
                    },
                },
            )
        return {
            "title": "LLM cross-day replan proposal",
            "summary": "Rebalances the selected nodes with concrete updated details.",
            "reasons": ["The affected nodes need pacing adjustment."],
            "warnings": [],
            "operations": operations,
            "evidence": [{"id": "evidence-1", "kind": "planner_note", "text": "Generated from target node context."}],
        }

def fake_recommendation(plan_id, title, stay_area, day_trip, foods, score):
    return {
        "id": plan_id,
        "title": title,
        "theme": f"{stay_area} / {day_trip} / food-focused city pacing",
        "summary": f"Use {stay_area} as the base and keep {day_trip} as the nearby day trip.",
        "best_for": ["Food-focused first visit", "One nearby day trip"],
        "tradeoffs": ["Confirm dates and booking details before finalizing."],
        "confidence": score / 3,
        "stay_plan": {
            "anchor_area": stay_area,
            "rationale": "Easy transit and food access.",
            "hotel_switches": 0,
        },
        "mobility_plan": {
            "day_trip": {
                "destination": day_trip,
                "transport": "train",
                "transfer_pressure": "low",
                "rationale": "Simple same-day return route.",
            },
        },
        "food_plan": {
            "must_try": foods,
            "suggested_areas": [stay_area],
            "reservation_notes": ["Confirm opening hours after dates are set."],
        },
        "day_plans": [
            {
                "day": 1,
                "title": "Arrival and local food",
                "area": stay_area,
                "pace": "light",
                "blocks": [{"time_of_day": "evening", "type": "meal", "title": foods[0], "location": stay_area}],
            },
            {
                "day": 2,
                "title": f"{day_trip} day trip",
                "area": day_trip,
                "pace": "moderate",
                "blocks": [{"time_of_day": "daytime", "type": "day_trip", "title": day_trip, "location": day_trip}],
            },
            {
                "day": 3,
                "title": "Slow city wrap-up",
                "area": stay_area,
                "pace": "light",
                "blocks": [{"time_of_day": "morning", "type": "experience", "title": f"{stay_area} neighborhood walk"}],
            },
        ],
        "evidence": ["planner used stay, mobility, and experience research"],
        "missing_info": ["dates"],
        "warnings": [],
        "score": score,
    }


class PlanningBriefProvider(FakeProvider):
    def __init__(self):
        self.calls = []

    def generate_planning_brief(self, *, system_prompt, user_prompt):
        self.calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt})
        return {
            "mode": "initial_plan",
            "origin_message": "model normalized message",
            "duration_days": 4,
            "destination_candidates": ["福冈"],
            "interests": ["美食", "周边游"],
            "pace": "relaxed",
            "soft_preferences": ["不要太赶"],
        }


class FailingPlanningBriefProvider(FakeProvider):
    def generate_planning_brief(self, *, system_prompt, user_prompt):
        raise LlmProviderError(code="timeout_error", message="timeout", retryable=True)


class ClarificationProvider(FakeProvider):
    def __init__(self):
        self.clarification_calls = []

    def generate_clarification_decision(self, *, system_prompt, user_prompt):
        self.clarification_calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt})
        return {
            "should_ask": True,
            "questions": [
                {"id": "destination", "text": "你想去哪里？", "required": True},
                {"id": "duration_days", "text": "你想玩几天？", "required": True},
            ],
            "reason": "The request is missing destination and duration.",
        }


class NoClarificationProvider(FakeProvider):
    def __init__(self):
        self.clarification_calls = []

    def generate_clarification_decision(self, *, system_prompt, user_prompt):
        self.clarification_calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt})
        return {
            "should_ask": False,
            "questions": [],
            "reason": "The request has enough information.",
        }


class FailingClarificationProvider(FakeProvider):
    def generate_clarification_decision(self, *, system_prompt, user_prompt):
        raise LlmProviderError(code="timeout_error", message="clarification timeout", retryable=True)


class RoutingProvider(FakeProvider):
    def __init__(self):
        self.routing_calls = []

    def generate_replan_routing_decision(self, *, system_prompt, user_prompt):
        self.routing_calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt})
        return {
            "scope": "regenerate_recommendations",
            "decision": "regenerate_recommendations",
            "output_kind": "recommendation_set",
            "affected_day_ids": [],
            "affected_node_ids": [],
            "reasons": ["LLM understood that the user wants a new set of recommendations."],
        }


class LegacyLocalProposalRoutingProvider(FakeProvider):
    def generate_replan_routing_decision(self, *, system_prompt, user_prompt):
        return {
            "scope": "lightweight_research",
            "decision": "local_proposal",
            "output_kind": "answer",
            "affected_day_ids": ["day-1"],
            "affected_node_ids": ["node-1"],
            "reasons": ["Legacy router returned deprecated local proposal"],
        }


class SpecialistProvider(FakeProvider):
    def __init__(self):
        self.specialist_calls = []

    def generate_specialist_selection(self, *, system_prompt, user_prompt):
        self.specialist_calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt})
        return {
            "needs": ["weather", "ticket", "price"],
            "reasons": ["LLM identified weather, ticket, and price constraints."],
        }


class ConsultationProvider(FakeProvider):
    def __init__(self):
        self.answer_calls = []

    def generate_answer(self, *, system_prompt, user_prompt):
        self.answer_calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt})
        return "consultative answer; no trip mutation"


class ExplodingPlanningBriefProvider(FakeProvider):
    def generate_planning_brief(self, *, system_prompt, user_prompt):
        raise RuntimeError("unexpected bug")


class MultiOptionProvider(FakeProvider):
    def generate_research(self, *, domain, system_prompt, user_prompt):
        payload = super().generate_research(domain=domain, system_prompt=system_prompt, user_prompt=user_prompt)
        if domain == "stay":
            payload["options"] = [
                {"id": "stay-1", "label": "Hakata Station", "anchorArea": "Hakata Station", "rationale": "Easy transit."},
                {"id": "stay-2", "label": "Tenjin", "anchorArea": "Tenjin", "rationale": "Good food access."},
            ]
        if domain == "mobility":
            payload["options"] = [
                {"id": "mobility-1", "label": "Dazaifu day trip", "destination": "Dazaifu", "transport": "train"},
                {"id": "mobility-2", "label": "Yanagawa day trip", "destination": "Yanagawa", "transport": "train"},
            ]
        return payload


class AnswerProvider(FakeProvider):
    def __init__(self):
        self.answer_calls = []

    def generate_answer(self, *, system_prompt, user_prompt):
        self.answer_calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt})
        return "model says this is a good lightweight answer"


class LowEvidenceProvider(FakeProvider):
    def generate_research(self, *, domain, system_prompt, user_prompt):
        payload = super().generate_research(domain=domain, system_prompt=system_prompt, user_prompt=user_prompt)
        payload["evidence"] = []
        payload["confidence"] = 0.1
        return payload

    def generate_recommendations(self, *, system_prompt, user_prompt):
        recommendations = super().generate_recommendations(system_prompt=system_prompt, user_prompt=user_prompt)["recommendations"]
        for item in recommendations:
            item["evidence"] = []
            item["score"] = 0.1
        return {"recommendations": recommendations}


class RecommendationPlannerProvider(FakeProvider):
    def __init__(self):
        self.planner_calls = []

    def generate_planning_brief(self, *, system_prompt, user_prompt):
        return {
            "mode": "initial_plan",
            "origin_message": user_prompt,
            "duration_days": 3,
            "destination_candidates": ["京都"],
            "interests": ["美食", "周边游"],
        }

    def generate_research(self, *, domain, system_prompt, user_prompt):
        payload = super().generate_research(domain=domain, system_prompt=system_prompt, user_prompt=user_prompt)
        if domain == "stay":
            payload["options"] = [{"id": "stay-1", "label": "Kyoto Station Hotel", "anchorArea": "Kyoto Station"}]
        if domain == "mobility":
            payload["options"] = [{"id": "mobility-1", "label": "Nara day trip", "destination": "Nara"}]
        if domain == "experience":
            payload["options"] = [{"id": "exp-1", "title": "Kyoto food plan"}]
        return payload

    def generate_recommendations(self, *, system_prompt, user_prompt):
        self.planner_calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt})
        return {
            "recommendations": [
                {
                    "id": "plan-1",
                    "title": "Kyoto Station base with Nara day trip",
                    "theme": "Kyoto Station / Nara / food",
                    "summary": "A complete planner-generated Kyoto plan.",
                    "best_for": ["Food-focused first visit"],
                    "tradeoffs": ["Requires checking restaurant reservation windows."],
                    "confidence": 0.86,
                    "stay_plan": {
                        "anchor_area": "Kyoto Station",
                        "rationale": "Convenient rail base for city and Nara.",
                        "hotel_switches": 0,
                    },
                    "mobility_plan": {
                        "day_trip": {
                            "destination": "Nara",
                            "transport": "train",
                            "transfer_pressure": "low",
                            "rationale": "Simple same-day return route.",
                        },
                    },
                    "food_plan": {
                        "must_try": ["錦市場食べ歩き", "湯豆腐", "抹茶スイーツ"],
                        "suggested_areas": ["Nishiki Market", "Kyoto Station"],
                        "reservation_notes": ["Confirm opening hours after dates are set."],
                    },
                    "day_plans": [
                        {
                            "day": 1,
                            "title": "Arrival and Kyoto food",
                            "area": "Kyoto Station",
                            "pace": "light",
                            "blocks": [
                                {"time_of_day": "evening", "type": "meal", "title": "湯豆腐 dinner", "location": "Kyoto Station"}
                            ],
                        },
                        {
                            "day": 2,
                            "title": "Nara day trip",
                            "area": "Nara",
                            "pace": "moderate",
                            "blocks": [
                                {"time_of_day": "daytime", "type": "day_trip", "title": "Nara", "location": "Nara"}
                            ],
                        },
                        {
                            "day": 3,
                            "title": "Nishiki Market and flexible city time",
                            "area": "Kyoto",
                            "pace": "light",
                            "blocks": [
                                {"time_of_day": "morning", "type": "experience", "title": "Nishiki Market food walk"}
                            ],
                        },
                    ],
                    "evidence": ["planner used stay, mobility, and experience research"],
                    "missing_info": ["dates"],
                    "warnings": [],
                    "score": 2.4,
                },
                {
                    "id": "plan-2",
                    "title": "Kyoto food-first slow plan",
                    "theme": "food / slow city",
                    "summary": "Second complete planner-generated plan.",
                    "best_for": ["Slow pacing"],
                    "tradeoffs": ["Less time for shopping."],
                    "confidence": 0.8,
                    "stay_plan": {
                        "anchor_area": "Kyoto Station",
                        "rationale": "Stable base.",
                        "hotel_switches": 0,
                    },
                    "mobility_plan": {"day_trip": {"destination": "Nara", "transport": "train"}},
                    "food_plan": {"must_try": ["obanzai dinner"], "suggested_areas": ["Kyoto Station"], "reservation_notes": []},
                    "day_plans": [
                        {"day": 1, "title": "Food arrival", "blocks": [{"time_of_day": "evening", "type": "meal", "title": "obanzai dinner"}]},
                        {"day": 2, "title": "Nara", "blocks": [{"time_of_day": "daytime", "type": "day_trip", "title": "Nara"}]},
                        {"day": 3, "title": "Cafe time", "blocks": [{"time_of_day": "morning", "type": "experience", "title": "Kyoto cafe morning"}]},
                    ],
                    "evidence": ["planner evidence"],
                    "missing_info": [],
                    "warnings": [],
                    "score": 2.2,
                },
                {
                    "id": "plan-3",
                    "title": "Kyoto balanced first visit",
                    "theme": "balanced",
                    "summary": "Third complete planner-generated plan.",
                    "best_for": ["Balanced trip"],
                    "tradeoffs": ["Needs final booking details."],
                    "confidence": 0.78,
                    "stay_plan": {
                        "anchor_area": "Kyoto Station",
                        "rationale": "Easy transfers.",
                        "hotel_switches": 0,
                    },
                    "mobility_plan": {"day_trip": {"destination": "Nara", "transport": "train"}},
                    "food_plan": {"must_try": ["matcha sweets"], "suggested_areas": ["Kyoto"], "reservation_notes": []},
                    "day_plans": [
                        {"day": 1, "title": "Arrival", "blocks": [{"time_of_day": "evening", "type": "meal", "title": "matcha sweets"}]},
                        {"day": 2, "title": "Nara", "blocks": [{"time_of_day": "daytime", "type": "day_trip", "title": "Nara"}]},
                        {"day": 3, "title": "City", "blocks": [{"time_of_day": "morning", "type": "experience", "title": "Kyoto city walk"}]},
                    ],
                    "evidence": ["planner evidence"],
                    "missing_info": [],
                    "warnings": [],
                    "score": 2.1,
                },
            ],
        }


class FailingRecommendationPlannerProvider(RecommendationPlannerProvider):
    def generate_recommendations(self, *, system_prompt, user_prompt):
        raise LlmProviderError(code="timeout_error", message="planner timeout", retryable=True)


class FailingReplanProposalProvider(FakeProvider):
    def generate_replan_proposal(self, *, system_prompt, user_prompt):
        raise LlmProviderError(code="timeout_error", message="replan timeout", retryable=True)


class ReplanWrongTargetProvider(FakeProvider):
    def generate_replan_proposal(self, *, system_prompt, user_prompt):
        return {
            "title": "Unsafe proposal",
            "summary": "Attempts to update a node outside targetNodes.",
            "operations": [
                {
                    "type": "UpdateNode",
                    "day_id": "day-9",
                    "node_id": "not-a-target",
                    "patch": {"title": "Unsafe update"},
                },
            ],
        }


class IncompleteReplanProposalProvider(FakeProvider):
    def generate_replan_proposal(self, *, system_prompt, user_prompt):
        return {
            "operations": [
                {
                    "type": "UpdateNode",
                    "day_id": "day-1",
                    "node_id": "node-1",
                    "patch": {"title": "Less rushed morning"},
                },
            ],
        }


class ReplanRecordingProvider(FakeProvider):
    def __init__(self):
        self.research_calls = []
        self.replan_prompts = []

    def generate_research(self, *, domain, system_prompt, user_prompt):
        self.research_calls.append(domain)
        raise LlmProviderError(code="timeout_error", message="research should not run for replan", retryable=True)

    def generate_replan_proposal(self, *, system_prompt, user_prompt):
        self.replan_prompts.append(user_prompt)
        return super().generate_replan_proposal(system_prompt=system_prompt, user_prompt=user_prompt)


class WeatherContextProvider(FakeProvider):
    def __init__(self):
        self.weather_calls = []
        self.experience_prompts = []

    def get_weather_context(self, *, planning_brief):
        self.weather_calls.append(planning_brief.destination_candidates)
        return {
            "source": "test_weather_api",
            "destination": "Kyoto",
            "daily": [
                {"date": "2026-07-20", "weather": "rain", "temperature_max_c": 29},
            ],
            "warnings": ["Rain likely; keep indoor alternatives."],
        }

    def generate_research(self, *, domain, system_prompt, user_prompt):
        if domain == "experience":
            self.experience_prompts.append(user_prompt)
        return super().generate_research(domain=domain, system_prompt=system_prompt, user_prompt=user_prompt)


class ApiContextProvider(WeatherContextProvider):
    def __init__(self):
        super().__init__()
        self.stay_prompts = []
        self.mobility_prompts = []

    def get_stay_context(self, *, planning_brief):
        return {"source": "test_hotel_api", "candidates": [{"name": "Test Hotel", "available": True}]}

    def get_mobility_context(self, *, planning_brief):
        return {"source": "test_map_api", "routes": [{"mode": "train", "duration_minutes": 45}]}

    def generate_research(self, *, domain, system_prompt, user_prompt):
        if domain == "stay":
            self.stay_prompts.append(user_prompt)
        if domain == "mobility":
            self.mobility_prompts.append(user_prompt)
        return super().generate_research(domain=domain, system_prompt=system_prompt, user_prompt=user_prompt)


class FailingWeatherContextProvider(WeatherContextProvider):
    def get_weather_context(self, *, planning_brief):
        raise RuntimeError("weather down")


class FailingStayMobilityApiProvider(ApiContextProvider):
    def get_stay_context(self, *, planning_brief):
        raise RuntimeError("hotel api down")

    def get_mobility_context(self, *, planning_brief):
        raise RuntimeError("mobility api down")


class FailingProvider:
    def generate_clarification_decision(self, *, system_prompt, user_prompt):
        return {"should_ask": False, "questions": [], "reason": "Continue to graph failure test."}

    def generate_research(self, *, domain, system_prompt, user_prompt):
        raise LlmProviderError(code="timeout_error", message="timeout", retryable=True)


class FailingStayRecordingProvider(FakeProvider):
    def __init__(self):
        self.calls = []

    def generate_research(self, *, domain, system_prompt, user_prompt):
        self.calls.append(domain)
        if domain == "stay":
            raise LlmProviderError(code="timeout_error", message="timeout", retryable=True)
        return super().generate_research(domain=domain, system_prompt=system_prompt, user_prompt=user_prompt)


class FailingAnswerProvider(FakeProvider):
    def generate_answer(self, *, system_prompt, user_prompt):
        raise LlmProviderError(code="timeout_error", message="answer timeout", retryable=True)


class ExplodingAnswerProvider(FakeProvider):
    def generate_answer(self, *, system_prompt, user_prompt):
        raise RuntimeError("unexpected provider failure")


class RecordingAdvisor:
    def __init__(self):
        self.calls = []

    def handle_request(self, **kwargs):
        self.calls.append(kwargs)
        return {"kind": "answer", "text": "advisor path"}


class SequencedAdvisor:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def handle_request(self, **kwargs):
        self.calls.append(kwargs)
        return self.results.pop(0)


class PythonAgentTest(unittest.TestCase):
    def test_planning_brief_builder_uses_llm_provider_first(self):
        provider = PlanningBriefProvider()
        builder = PlanningBriefBuilder(provider=provider)

        brief = builder.build_initial_planning_brief("帮我规划一个福冈四日游，想吃好吃的")

        self.assertEqual(brief.duration_days, 4)
        self.assertEqual(brief.destination_candidates, ["福冈"])
        self.assertEqual(brief.interests, ["美食", "周边游"])
        self.assertEqual(provider.calls[0]["user_prompt"], "帮我规划一个福冈四日游，想吃好吃的")

    def test_planning_brief_builder_does_not_guess_fields_when_llm_fails(self):
        builder = PlanningBriefBuilder(provider=FailingPlanningBriefProvider())

        brief = builder.build_initial_planning_brief("帮我规划一个福冈三日游，想吃好吃的，也想安排一天周边游")

        self.assertIsNone(brief.duration_days)
        self.assertEqual(brief.destination_candidates, [])
        self.assertEqual(brief.interests, [])
        self.assertEqual(brief.builder_source, "fallback")
        self.assertEqual(brief.builder_fallback_reason, "timeout_error")

    def test_planning_brief_builder_does_not_swallow_unexpected_errors(self):
        builder = PlanningBriefBuilder(provider=ExplodingPlanningBriefProvider())

        with self.assertRaises(RuntimeError):
            builder.build_initial_planning_brief("帮我规划一个福冈三日游")

    def test_initial_plan_returns_exactly_three_recommendations_by_default(self):
        graph = TripPlanningGraph(provider=FakeProvider())

        result = graph.run_initial_plan("Plan a 3-day Fukuoka food trip")

        self.assertEqual(len(result["recommendationSet"]["recommendations"]), 3)

    def test_skeleton_plan_does_not_default_unknown_duration_to_three_days(self):
        graph = TripPlanningGraph(provider=FakeProvider())

        state = graph.run(
            TripPlanningGraphRequest(
                run_id="test-run",
                user_id="user-1",
                mode="initial_plan",
                planning_brief=PlanningBrief(mode="initial_plan", origin_message="Plan a trip"),
            ),
        )

        self.assertEqual(state.skeleton_plan["day_frames"], [])

    def test_research_result_accepts_string_options_from_model(self):
        result = ResearchResult(domain="stay", options=["Hakata Station area"])

        self.assertEqual(result.options[0].label, "Hakata Station area")

    def test_initial_plan_returns_frontend_recommendation_schema(self):
        graph = TripPlanningGraph(provider=FakeProvider())

        result = graph.run_initial_plan("Plan a 3-day Fukuoka food trip")

        self.assertEqual(result["kind"], "recommendation_set")
        recommendation_set = result["recommendationSet"]
        self.assertEqual(recommendation_set["type"], "recommendation_set")
        first = recommendation_set["recommendations"][0]
        self.assertEqual(first["stay_plan"]["anchor_area"], "Hakata Station anchor")
        self.assertEqual(first["mobility_plan"]["day_trip"]["destination"], "Dazaifu")
        self.assertIn("Yatai and ramen evening", first["food_plan"]["must_try"])
        self.assertGreaterEqual(len(first["day_plans"]), 3)
        self.assertEqual(result["trace"][-1]["node"], "finalize_output_node")
        trace_nodes = [item["node"] for item in result["trace"]]
        self.assertIn("candidate_merge_node", trace_nodes)
        self.assertIn("recommendation_planner_node", trace_nodes)
        self.assertIn("validate_candidates_node", trace_nodes)

    def test_initial_plan_trace_records_each_graph_node_once(self):
        graph = TripPlanningGraph(provider=FakeProvider())

        result = graph.run_initial_plan("Plan a 3-day Fukuoka food trip")

        trace_counts = Counter(item["node"] for item in result["trace"])
        self.assertEqual(trace_counts["skeleton_planning_node"], 1)
        self.assertEqual(trace_counts["stay_research_node"], 1)
        self.assertEqual(trace_counts["mobility_research_node"], 1)
        self.assertEqual(trace_counts["experience_research_node"], 1)
        self.assertEqual(trace_counts["research_barrier_node"], 1)
        self.assertEqual(trace_counts["candidate_merge_node"], 1)
        self.assertEqual(trace_counts["recommendation_planner_node"], 1)
        self.assertEqual(trace_counts["validate_candidates_node"], 1)
        self.assertEqual(trace_counts["finalize_output_node"], 1)

    def test_initial_plan_recommendations_do_not_repeat_same_title(self):
        graph = TripPlanningGraph(provider=MultiOptionProvider())

        result = graph.run_initial_plan("Plan a 3-day Fukuoka food trip")

        recommendations = result["recommendationSet"]["recommendations"]
        titles = [item["title"] for item in recommendations]
        self.assertEqual(len(recommendations), 3)
        self.assertEqual(len(titles), len(set(titles)))

    def test_initial_plan_uses_llm_planning_brief_for_user_intent(self):
        graph = TripPlanningGraph(provider=PlanningBriefProvider())

        result = graph.run_initial_plan("帮我规划一个福冈三日游，想吃好吃的，也想安排一天周边游")

        intent = result["recommendationSet"]["trip_intent"]
        self.assertEqual(intent["destination"], "福冈")
        self.assertEqual(intent["duration_days"], 4)
        self.assertIn("美食", intent["interests"])
        self.assertIn("周边游", intent["interests"])

    def test_day_trip_option_is_not_used_as_food_when_food_highlights_exist(self):
        class DayTripNamedExperienceProvider(FakeProvider):
            def generate_research(self, *, domain, system_prompt, user_prompt):
                payload = super().generate_research(domain=domain, system_prompt=system_prompt, user_prompt=user_prompt)
                if domain == "experience":
                    payload["options"] = [
                        {
                            "id": "exp-1",
                            "title": "Dazaifu Day Trip",
                            "foodHighlights": ["博多拉面", "明太子", "屋台小吃"],
                            "cityExperiences": ["栉田神社散步", "天神咖啡休息"],
                        },
                    ]
                return payload

            def generate_recommendations(self, *, system_prompt, user_prompt):
                recommendation = fake_recommendation(
                    "plan-1",
                    "Hakata food plan with Dazaifu day trip",
                    "Hakata",
                    "Dazaifu",
                    ["博多拉面", "明太子", "屋台小吃"],
                    2.4,
                )
                return {"recommendations": [recommendation, fake_recommendation("plan-2", "Plan 2", "Tenjin", "Yanagawa", ["咖啡甜点"], 2.2), fake_recommendation("plan-3", "Plan 3", "Hakata", "Dazaifu", ["市场小吃"], 2.1)]}

        graph = TripPlanningGraph(provider=DayTripNamedExperienceProvider())

        result = graph.run_initial_plan("帮我规划一个福冈三日游，想吃好吃的，也想安排一天周边游")

        first = result["recommendationSet"]["recommendations"][0]
        self.assertIn("博多拉面", first["food_plan"]["must_try"])
        self.assertIn("屋台小吃", first["food_plan"]["must_try"])
        self.assertNotIn("Dazaifu Day Trip", first["food_plan"]["must_try"])
        meal_titles = [
            block["title"]
            for day in first["day_plans"]
            for block in day["blocks"]
            if block["type"] == "meal"
        ]
        self.assertNotIn("Dazaifu Day Trip", meal_titles)

    def test_day_trip_food_does_not_replace_first_city_dinner(self):
        class DayTripFoodProvider(FakeProvider):
            def generate_planning_brief(self, *, system_prompt, user_prompt):
                return {
                    "mode": "initial_plan",
                    "origin_message": user_prompt,
                    "duration_days": 3,
                    "destination_candidates": ["福冈"],
                    "interests": ["美食", "周边游"],
                }

            def generate_research(self, *, domain, system_prompt, user_prompt):
                payload = super().generate_research(domain=domain, system_prompt=system_prompt, user_prompt=user_prompt)
                if domain == "experience":
                    payload["options"] = [
                        {
                            "id": "exp-1",
                            "title": "Dazaifu food walk",
                            "foodHighlights": ["Dazaifu market manju", "Umezono soba"],
                            "cityExperiences": ["Visit Dazaifu Tenmangu shrine"],
                        },
                    ]
                return payload

            def generate_recommendations(self, *, system_prompt, user_prompt):
                recommendation = fake_recommendation(
                    "plan-1",
                    "Hakata city dinner with Dazaifu food day",
                    "Hakata",
                    "Dazaifu",
                    ["Hakata yatai dinner", "Dazaifu market manju", "Umezono soba"],
                    2.4,
                )
                recommendation["day_plans"][0]["blocks"][0]["title"] = "Hakata yatai dinner"
                recommendation["day_plans"][2]["blocks"][0]["title"] = "Hakata neighborhood cafe walk"
                return {"recommendations": [recommendation, fake_recommendation("plan-2", "Plan 2", "Tenjin", "Yanagawa", ["Tenjin dinner"], 2.2), fake_recommendation("plan-3", "Plan 3", "Hakata", "Dazaifu", ["Market breakfast"], 2.1)]}

        graph = TripPlanningGraph(provider=DayTripFoodProvider())

        result = graph.run_initial_plan("帮我规划一个福冈三日游，想吃好吃的，也想安排一天周边游")

        first = result["recommendationSet"]["recommendations"][0]
        first_day_meals = [
            block["title"]
            for block in first["day_plans"][0]["blocks"]
            if block["type"] == "meal"
        ]
        day_three_experiences = [
            block["title"]
            for block in first["day_plans"][2]["blocks"]
            if block["type"] == "experience"
        ]
        self.assertEqual(first_day_meals, ["Hakata yatai dinner"])
        self.assertNotIn("Dazaifu market manju", first_day_meals)
        self.assertNotIn("Visit Dazaifu Tenmangu shrine", day_three_experiences)

    def test_recommendation_composer_does_not_invent_fukuoka_specific_content(self):
        class KyotoProvider(FakeProvider):
            def generate_planning_brief(self, *, system_prompt, user_prompt):
                return {
                    "mode": "initial_plan",
                    "origin_message": user_prompt,
                    "duration_days": 3,
                    "destination_candidates": ["京都"],
                    "interests": ["美食", "周边游"],
                }

            def generate_research(self, *, domain, system_prompt, user_prompt):
                payload = super().generate_research(domain=domain, system_prompt=system_prompt, user_prompt=user_prompt)
                if domain == "stay":
                    payload["options"] = [{"id": "stay-1", "label": "Kyoto Station", "anchorArea": "Kyoto Station"}]
                if domain == "mobility":
                    payload["options"] = [{"id": "mobility-1", "label": "Nara day trip", "destination": "Nara"}]
                if domain == "experience":
                    payload["options"] = [{"id": "exp-1", "title": "slow city walk"}]
                return payload

        graph = TripPlanningGraph(provider=KyotoProvider())

        result = graph.run_initial_plan("帮我规划一个京都三日游，想吃好吃的，也想安排一天周边游")

        serialized = json.dumps(result["recommendationSet"]["recommendations"], ensure_ascii=False)
        for invented_item in ["博多", "明太子", "牛肠锅", "屋台", "天神", "中洲"]:
            self.assertNotIn(invented_item, serialized)

    def test_recommendation_planner_node_generates_complete_recommendations(self):
        provider = RecommendationPlannerProvider()
        graph = TripPlanningGraph(provider=provider)

        result = graph.run_initial_plan("帮我规划一个京都三日游，想吃好吃的，也想安排一天周边游")

        trace_nodes = [item["node"] for item in result["trace"]]
        first = result["recommendationSet"]["recommendations"][0]
        self.assertEqual(len(provider.planner_calls), 1)
        self.assertIn("candidateContext", provider.planner_calls[0]["user_prompt"])
        self.assertIn("candidate_merge_node", trace_nodes)
        self.assertIn("recommendation_planner_node", trace_nodes)
        self.assertNotIn("recommendation_enrichment_node", trace_nodes)
        self.assertEqual(first["title"], "Kyoto Station base with Nara day trip")
        self.assertIn("錦市場食べ歩き", first["food_plan"]["must_try"])
        self.assertEqual(len(result["recommendationSet"]["recommendations"]), 3)

    def test_recommendation_planner_failure_returns_graph_error_instead_of_placeholder_recommendations(self):
        graph = TripPlanningGraph(provider=FailingRecommendationPlannerProvider())

        result = graph.run_initial_plan("帮我规划一个京都三日游，想吃好吃的，也想安排一天周边游")

        planner_trace = next(item for item in result["trace"] if item["node"] == "recommendation_planner_node")
        self.assertEqual(result["kind"], "graph_error")
        self.assertEqual(result["graphError"]["error_code"], "timeout_error")
        self.assertEqual(planner_trace["status"], "error")
        self.assertEqual(planner_trace["error_code"], "timeout_error")
        self.assertNotIn("recommendationSet", result)

    def test_recommendation_planner_accepts_camel_case_llm_payload(self):
        payload = {
            "recommendations": [
                {
                    "id": "plan-1",
                    "title": "Plan 1",
                    "theme": "Food",
                    "summary": "Summary",
                    "bestFor": ["Food lovers"],
                    "tradeoffs": [],
                    "stayPlan": {"anchorArea": "Station", "rationale": "Easy", "hotelSwitches": 0},
                    "mobilityPlan": {"dayTrip": {"destination": "Nara", "transferPressure": "low"}},
                    "foodPlan": {"mustTry": ["tofu"], "suggestedAreas": ["Station"], "reservationNotes": []},
                    "dayPlans": [
                        {"day": 1, "title": "Day 1", "blocks": [{"timeOfDay": "evening", "type": "meal", "title": "tofu"}]}
                    ],
                    "evidence": ["planner evidence"],
                    "missingInfo": [],
                    "warnings": [],
                    "score": 2.0,
                },
                {
                    "id": "plan-2",
                    "title": "Plan 2",
                    "theme": "Food",
                    "summary": "Summary",
                    "stayPlan": {"anchorArea": "Station", "rationale": "Easy"},
                    "mobilityPlan": {"dayTrip": {"destination": "Nara"}},
                    "foodPlan": {"mustTry": ["soba"]},
                    "dayPlans": [{"day": 1, "title": "Day 1", "blocks": [{"timeOfDay": "evening", "type": "meal", "title": "soba"}]}],
                    "evidence": ["planner evidence"],
                    "score": 2.0,
                },
                {
                    "id": "plan-3",
                    "title": "Plan 3",
                    "theme": "Food",
                    "summary": "Summary",
                    "stayPlan": {"anchorArea": "Station", "rationale": "Easy"},
                    "mobilityPlan": {"dayTrip": {"destination": "Nara"}},
                    "foodPlan": {"mustTry": ["matcha"]},
                    "dayPlans": [{"day": 1, "title": "Day 1", "blocks": [{"timeOfDay": "evening", "type": "meal", "title": "matcha"}]}],
                    "evidence": ["planner evidence"],
                    "score": 2.0,
                },
            ],
        }

        recommendations = parse_recommendations(payload)

        self.assertEqual(recommendations[0].stay_plan.anchor_area, "Station")
        self.assertEqual(recommendations[0].mobility_plan.day_trip.transfer_pressure, "low")
        self.assertEqual(recommendations[0].food_plan.must_try, ["tofu"])
        self.assertEqual(recommendations[0].day_plans[0].blocks[0].time_of_day, "evening")

    def test_experience_research_includes_weather_api_context(self):
        provider = WeatherContextProvider()
        graph = TripPlanningGraph(provider=provider)

        result = graph.run_initial_plan("帮我规划一个京都三日游，想吃好吃的，也想安排一天周边游")

        self.assertEqual(result["kind"], "recommendation_set")
        self.assertEqual(provider.weather_calls, [[]])
        self.assertIn("Weather API context", provider.experience_prompts[0])
        self.assertIn("Rain likely", provider.experience_prompts[0])

    def test_stay_and_mobility_research_include_api_context_hooks(self):
        provider = ApiContextProvider()
        graph = TripPlanningGraph(provider=provider)

        result = graph.run_initial_plan("帮我规划一个京都三日游，想吃好吃的，也想安排一天周边游")

        self.assertEqual(result["kind"], "recommendation_set")
        self.assertIn("Stay API context", provider.stay_prompts[0])
        self.assertIn("Test Hotel", provider.stay_prompts[0])
        self.assertIn("Mobility API context", provider.mobility_prompts[0])
        self.assertIn("duration_minutes", provider.mobility_prompts[0])

    def test_weather_api_failure_does_not_abort_experience_research(self):
        provider = FailingWeatherContextProvider()
        graph = TripPlanningGraph(provider=provider)

        result = graph.run_initial_plan("帮我规划一个京都三日游，想吃好吃的，也想安排一天周边游")

        self.assertEqual(result["kind"], "recommendation_set")
        self.assertIn("Weather API unavailable", provider.experience_prompts[0])

    def test_stay_and_mobility_api_failures_do_not_abort_research(self):
        provider = FailingStayMobilityApiProvider()
        graph = TripPlanningGraph(provider=provider)

        result = graph.run_initial_plan("帮我规划一个京都三日游，想吃好吃的，也想安排一天周边游")

        self.assertEqual(result["kind"], "recommendation_set")
        self.assertIn("Stay API unavailable", provider.stay_prompts[0])
        self.assertIn("Mobility API unavailable", provider.mobility_prompts[0])

    def test_travel_advisor_routes_initial_plan_to_graph(self):
        advisor = TravelAdvisor(graph=TripPlanningGraph(provider=PlanningBriefProvider()))

        result = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="帮我规划一个福冈三日游，想吃好吃的，也想安排一天周边游",
        )

        self.assertEqual(result["kind"], "trip_board")
        self.assertEqual(result["routing"]["decision"], "graph_replan")
        self.assertEqual(result["sourceRecommendationSet"]["trip_intent"]["destination"], "福冈")
        self.assertEqual(result["trip"]["source_recommendation_id"], "plan-1")

    def test_travel_advisor_handles_direct_answer_and_consultative_replace_text(self):
        proposal_service = ProposalService()
        advisor = TravelAdvisor(
            graph=TripPlanningGraph(provider=AnswerProvider()),
            proposal_service=proposal_service,
        )
        trip = {
            "id": "trip-1",
            "version": 1,
            "days": [{"id": "day-1", "nodes": [{"id": "node-1", "type": "hotel", "title": "Old Hotel"}]}],
        }

        direct = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="这个酒店怎么样？",
            intent={"kind": "ask"},
        )
        local = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="帮我换掉这个酒店",
            trip=trip,
            intent={
                "kind": "replace",
                "scope": "node",
                "node_id": "node-1",
                "replacement_type": "hotel",
                "affected_day_ids": ["day-1"],
            },
        )

        self.assertEqual(direct["kind"], "answer")
        self.assertEqual(direct["routing"]["decision"], "direct_answer")
        self.assertEqual(local["kind"], "answer")
        self.assertEqual(local["routing"]["decision"], "lightweight_research")
        self.assertEqual(local["routing"]["specialistSelection"]["needs"], ["stay"])
        self.assertEqual(len(proposal_service.list_proposals()), 0)

    def test_travel_advisor_routes_js_replace_intents_to_lightweight_consultation(self):
        advisor = TravelAdvisor(graph=TripPlanningGraph(provider=AnswerProvider()))
        trip = {
            "id": "trip-1",
            "version": 1,
            "days": [{"id": "day-1", "nodes": [{"id": "node-1", "type": "hotel", "title": "Old Hotel"}]}],
        }

        result = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="Replace this hotel",
            trip=trip,
            intent={
                "kind": "replace_hotel",
                "scope": "node",
                "node_id": "node-1",
                "affected_day_ids": ["day-1"],
            },
        )

        self.assertEqual(result["kind"], "answer")
        self.assertEqual(result["routing"]["decision"], "lightweight_research")
        self.assertEqual(result["routing"]["specialistSelection"]["needs"], ["stay"])

    def test_explicit_replan_replace_intent_routes_to_graph_proposal(self):
        advisor = TravelAdvisor(graph=TripPlanningGraph(provider=FakeProvider()))
        trip = {
            "id": "trip-1",
            "version": 1,
            "days": [{"id": "day-1", "nodes": [{"id": "node-1", "type": "hotel", "title": "Old Hotel"}]}],
        }

        result = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="Replace this hotel as part of a day replan",
            trip=trip,
            intent={
                "kind": "replace_hotel",
                "mode": "day_replan",
                "scope": "day",
                "node_id": "node-1",
                "affected_day_ids": ["day-1"],
                "can_close_locally": False,
            },
        )

        self.assertEqual(result["kind"], "proposal")
        self.assertEqual(result["routing"]["decision"], "graph_replan")

    def test_deprecated_local_proposal_router_output_respects_explicit_replan(self):
        advisor = TravelAdvisor(graph=TripPlanningGraph(provider=LegacyLocalProposalRoutingProvider()))
        trip = {
            "id": "trip-1",
            "version": 1,
            "days": [{"id": "day-1", "nodes": [{"id": "node-1", "type": "hotel", "title": "Old Hotel"}]}],
        }

        result = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="Replan this day and replace this hotel",
            trip=trip,
            intent={
                "kind": "replace_hotel",
                "mode": "day_replan",
                "node_id": "node-1",
                "affected_day_ids": ["day-1"],
                "can_close_locally": False,
            },
        )

        self.assertEqual(result["kind"], "proposal")
        self.assertEqual(result["routing"]["decision"], "graph_replan")

    def test_travel_advisor_asks_clarification_before_under_specified_initial_plan(self):
        provider = ClarificationProvider()
        advisor = TravelAdvisor(graph=TripPlanningGraph(provider=provider))

        result = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="Plan a trip for me",
            intent={"kind": "initial_plan"},
        )

        parsed = ClarificationQuestionResponse.model_validate(result)
        self.assertEqual(parsed.kind, "clarification_question")
        self.assertEqual(parsed.routing["decision"], "clarification_question")
        self.assertIn("destination", [question["id"] for question in parsed.questions])
        self.assertIn("duration_days", [question["id"] for question in parsed.questions])
        self.assertEqual(len(provider.clarification_calls), 1)

    def test_travel_advisor_does_not_clarify_when_initial_plan_has_destination_and_duration(self):
        class EnoughInfoProvider(NoClarificationProvider, PlanningBriefProvider):
            def __init__(self):
                self.clarification_calls = []
                self.calls = []

        provider = EnoughInfoProvider()
        advisor = TravelAdvisor(graph=TripPlanningGraph(provider=provider))

        result = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="Plan a 3-day Fukuoka trip with food and one day trip",
            intent={"kind": "initial_plan"},
        )

        self.assertEqual(result["kind"], "trip_board")
        self.assertEqual(len(provider.clarification_calls), 1)

    def test_travel_advisor_clarification_provider_failure_falls_back_to_safe_questions(self):
        advisor = TravelAdvisor(graph=TripPlanningGraph(provider=FailingClarificationProvider()))

        result = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="Plan a trip for me",
            intent={"kind": "initial_plan"},
        )

        self.assertEqual(result["kind"], "clarification_question")
        self.assertEqual(result["questions"][0]["id"], "destination")
        self.assertIn("fallback", result["routing"]["reasons"][0])

    def test_clarification_fallback_questions_are_readable_chinese(self):
        decision = ClarificationPolicy(provider=None).decide(
            user_message="帮我规划旅行",
            trip=None,
            intent={"kind": "initial_plan"},
        )

        self.assertEqual(decision.questions[0].text, "你想去哪个城市、国家或区域？")
        self.assertEqual(decision.questions[1].text, "大概玩几天？")

    def test_specialist_selector_fallback_understands_chinese_keywords(self):
        selection = SpecialistSelector(provider=None).select(
            user_message="帮我看下这个酒店，第三天下雨的话门票和交通会不会太贵，还想吃美食",
            intent={},
        )

        self.assertIn(ReplanNeed.STAY, selection.needs)
        self.assertIn(ReplanNeed.WEATHER, selection.needs)
        self.assertIn(ReplanNeed.TICKET, selection.needs)
        self.assertIn(ReplanNeed.MOBILITY, selection.needs)
        self.assertIn(ReplanNeed.PRICE, selection.needs)
        self.assertIn(ReplanNeed.EXPERIENCE, selection.needs)

    def test_travel_advisor_regenerates_trip_board_without_current_trip(self):
        advisor = TravelAdvisor(graph=TripPlanningGraph(provider=PlanningBriefProvider()))

        result = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="这三个方案我都不喜欢，帮我重新换一组三个",
            intent={"kind": "regenerate_recommendations", "can_close_locally": False},
        )

        self.assertEqual(result["kind"], "trip_board")
        self.assertEqual(result["routing"]["decision"], "regenerate_recommendations")
        self.assertEqual(result["routing"]["replan"]["scope"], ReplanScope.REGENERATE_RECOMMENDATIONS.value)
        self.assertEqual(result["trip"]["source_recommendation_id"], "plan-1")

    def test_travel_advisor_replan_records_scope_and_specialist_needs(self):
        advisor = TravelAdvisor(graph=TripPlanningGraph(provider=FakeProvider()))
        trip = {
            "id": "trip-1",
            "version": 1,
            "days": [
                {"id": "day-2", "nodes": [{"id": "node-2", "type": "activity", "title": "Outdoor garden"}]},
                {"id": "day-3", "nodes": [{"id": "node-3", "type": "activity", "title": "Museum"}]},
            ],
        }

        result = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="第二天可能下雨，还要看门票价格，帮我把第二天和第三天重新平衡一下",
            trip=trip,
            intent={
                "kind": "replan",
                "affected_day_ids": ["day-2", "day-3"],
                "affected_node_ids": ["node-2", "node-3"],
                "can_close_locally": False,
            },
        )

        self.assertEqual(result["kind"], "proposal")
        self.assertEqual(result["routing"]["replan"]["scope"], ReplanScope.CROSS_DAY_REPLAN.value)
        self.assertIn(ReplanNeed.WEATHER.value, result["routing"]["specialistSelection"]["needs"])
        self.assertIn(ReplanNeed.TICKET.value, result["routing"]["specialistSelection"]["needs"])
        self.assertIn(ReplanNeed.PRICE.value, result["routing"]["specialistSelection"]["needs"])

    def test_travel_advisor_uses_llm_replan_router_when_intent_is_underspecified(self):
        provider = RoutingProvider()
        advisor = TravelAdvisor(graph=TripPlanningGraph(provider=provider))

        result = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="这三套我都不喜欢，重新给我三套",
            intent={"kind": "ask"},
        )

        self.assertEqual(result["kind"], "trip_board")
        self.assertEqual(result["routing"]["decision"], "regenerate_recommendations")
        self.assertEqual(len(provider.routing_calls), 1)

    def test_travel_advisor_uses_llm_specialist_selector(self):
        provider = SpecialistProvider()
        advisor = TravelAdvisor(graph=TripPlanningGraph(provider=provider))

        result = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="明天可能下雨，还要看门票和价格",
            intent={"kind": "ask"},
        )

        self.assertEqual(result["kind"], "answer")
        self.assertEqual(result["routing"]["specialistSelection"]["needs"], ["weather", "ticket", "price"])
        self.assertEqual(result["routing"]["specialistSelection"]["optional"], ["weather", "ticket", "price"])
        self.assertEqual(len(provider.specialist_calls), 1)

    def test_free_text_replace_is_consultative_and_uses_lightweight_answer_provider(self):
        provider = ConsultationProvider()
        advisor = TravelAdvisor(graph=TripPlanningGraph(provider=provider))
        trip = {
            "id": "trip-1",
            "version": 1,
            "days": [{"id": "day-1", "nodes": [{"id": "node-1", "type": "hotel", "title": "Noisy Hotel"}]}],
        }

        result = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="帮我换一个安静点的酒店",
            trip=trip,
            intent={"kind": "replace_hotel", "node_id": "node-1", "affected_day_ids": ["day-1"]},
        )

        self.assertEqual(result["kind"], "answer")
        self.assertEqual(result["routing"]["decision"], "lightweight_research")
        self.assertEqual(result["routing"]["specialistSelection"]["needs"], ["stay"])
        self.assertEqual(result["text"], "consultative answer; no trip mutation")
        self.assertEqual(len(provider.answer_calls), 1)

    def test_specialist_selection_separates_required_node_capability_from_optional_user_capabilities(self):
        provider = ConsultationProvider()
        advisor = TravelAdvisor(graph=TripPlanningGraph(provider=provider))
        trip = {
            "id": "trip-1",
            "version": 1,
            "days": [{"id": "day-1", "nodes": [{"id": "node-1", "type": "hotel", "title": "Quiet Hotel"}]}],
        }

        result = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="Will the weather make taxi rides inconvenient near this hotel?",
            trip=trip,
            intent={"kind": "ask", "node_id": "node-1"},
        )

        selection = result["routing"]["specialistSelection"]
        self.assertEqual(result["routing"]["capabilityPlan"], selection)
        self.assertEqual(selection["required"], ["stay"])
        self.assertIn("weather", selection["optional"])
        self.assertIn("mobility", selection["optional"])
        self.assertEqual(selection["execution_mode"], "lightweight")
        self.assertEqual(set(selection["needs"]), {"stay", "weather", "mobility"})

    def test_node_tags_can_add_required_capabilities(self):
        provider = ConsultationProvider()
        advisor = TravelAdvisor(graph=TripPlanningGraph(provider=provider))
        trip = {
            "id": "trip-1",
            "version": 1,
            "days": [{"id": "day-1", "nodes": [{"id": "node-1", "type": "place", "tags": ["hotel"], "title": "Tagged Hotel"}]}],
        }

        result = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="Is this a good place to stay?",
            trip=trip,
            intent={"kind": "ask", "node_id": "node-1"},
        )

        self.assertIn("stay", result["routing"]["capabilityPlan"]["required"])

    def test_local_proposal_route_is_not_exposed_as_a_runtime_decision(self):
        from backend.agent.contracts.routing_and_proposal import EscalationDecision
        from backend.agent.lightweight_flows import LightweightFlows

        self.assertNotIn("local_proposal", [decision.value for decision in EscalationDecision])
        self.assertFalse(hasattr(LightweightFlows(), "local_proposal"))

    def test_lightweight_answer_uses_model_provider(self):
        provider = AnswerProvider()
        advisor = TravelAdvisor(graph=TripPlanningGraph(provider=provider))

        result = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="Is this hotel convenient?",
            intent={"kind": "ask"},
        )

        self.assertEqual(result["kind"], "answer")
        self.assertEqual(result["text"], "model says this is a good lightweight answer")
        self.assertEqual(len(provider.answer_calls), 1)

    def test_lightweight_research_uses_model_provider(self):
        provider = AnswerProvider()
        advisor = TravelAdvisor(graph=TripPlanningGraph(provider=provider))

        result = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="Research whether this museum is closed on Monday",
            intent={"kind": "research"},
        )

        self.assertEqual(result["kind"], "answer")
        self.assertEqual(result["routing"]["decision"], "lightweight_research")
        self.assertEqual(result["text"], "model says this is a good lightweight answer")
        self.assertEqual(len(provider.answer_calls), 1)

    def test_lightweight_answer_failure_returns_advisor_fallback(self):
        advisor = TravelAdvisor(graph=TripPlanningGraph(provider=FailingAnswerProvider()))

        result = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="Is this hotel convenient?",
            intent={"kind": "ask"},
        )

        self.assertEqual(result["kind"], "answer")
        self.assertEqual(result["fallback"]["decision"], "fallback_to_answer")
        self.assertEqual(result["fallback"]["source"], "lightweight")

    def test_unexpected_lightweight_answer_failure_returns_advisor_fallback(self):
        advisor = TravelAdvisor(graph=TripPlanningGraph(provider=ExplodingAnswerProvider()))

        result = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="Is this hotel convenient?",
            intent={"kind": "ask"},
        )

        self.assertEqual(result["kind"], "answer")
        self.assertEqual(result["fallback"]["decision"], "fallback_to_answer")
        self.assertEqual(result["fallback"]["error_code"], "unknown_error")

    def test_direct_answer_uses_discussion_brief_instead_of_initial_plan_brief(self):
        advisor = TravelAdvisor(graph=TripPlanningGraph(provider=AnswerProvider()))
        trip = {
            "id": "trip-1",
            "version": 1,
            "days": [{"id": "day-1", "nodes": [{"id": "node-1", "type": "hotel", "title": "Hotel"}]}],
        }

        result = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="Is this hotel convenient?",
            trip=trip,
            intent={"kind": "ask"},
        )

        self.assertEqual(result["kind"], "answer")
        self.assertEqual(result["planningBrief"]["mode"], "discussion_turn")
        self.assertIsNone(result["planningBrief"]["duration_days"])

    def test_graph_provider_failure_returns_graph_error_and_advisor_fallback(self):
        advisor = TravelAdvisor(graph=TripPlanningGraph(provider=FailingProvider()))

        result = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="Plan a 3-day Fukuoka food trip",
            intent={"kind": "initial_plan"},
        )

        self.assertEqual(result["kind"], "answer")
        self.assertEqual(result["fallback"]["decision"], "fallback_to_answer")
        self.assertEqual(result["fallback"]["graph_error"]["decision"], "retry_later")

    def test_graph_runs_research_branches_before_erroring_without_merge(self):
        provider = FailingStayRecordingProvider()
        graph = TripPlanningGraph(provider=provider)

        result = graph.run_initial_plan("Plan a 3-day Fukuoka food trip")

        trace_nodes = [item["node"] for item in result["trace"]]
        self.assertEqual(result["kind"], "graph_error")
        self.assertIn("stay_research_node", trace_nodes)
        self.assertIn("mobility_research_node", trace_nodes)
        self.assertIn("experience_research_node", trace_nodes)
        self.assertNotIn("finalize_output_node", trace_nodes)
        self.assertCountEqual(provider.calls, ["stay", "mobility", "experience"])

    def test_validate_candidates_marks_low_evidence_low_score_as_failed(self):
        graph = TripPlanningGraph(provider=LowEvidenceProvider())

        result = graph.run_initial_plan("Plan a 3-day Fukuoka food trip")

        self.assertEqual(result["kind"], "graph_error")
        self.assertEqual(result["graphError"]["error_code"], "candidate_validation_failed")
        validation_trace = next(item for item in result["trace"] if item["node"] == "validate_candidates_node")
        self.assertEqual(validation_trace["status"], "fail")
        first_candidate = validation_trace["candidate_results"][0]
        self.assertIn("missing_evidence", first_candidate["reasons"])
        self.assertIn("low_score", first_candidate["reasons"])

    def test_proposal_service_and_executor_apply_accepted_proposal(self):
        service = ProposalService()
        executor = ProposalExecutor()
        trip = {
            "id": "trip-1",
            "version": 1,
            "days": [{"id": "day-1", "nodes": [{"id": "node-1", "type": "hotel", "title": "Old Hotel"}]}],
        }
        proposal = {
            "proposal_id": "proposal-1",
            "trip_id": "trip-1",
            "base_version": 1,
            "scope": "node",
            "title": "Replace hotel",
            "summary": "Use a different hotel.",
            "operations": [
                {
                    "type": "ReplaceNode",
                    "day_id": "day-1",
                    "node_id": "node-1",
                    "replacement": {"id": "node-1", "type": "hotel", "title": "New Hotel"},
                },
            ],
        }

        stored = service.persist_proposal(proposal, current_trip_version=1)
        accepted = service.update_proposal_status(stored.proposal_id, "accepted")
        result = executor.execute(trip, accepted)

        self.assertEqual(result["trip"]["version"], 2)
        self.assertEqual(result["trip"]["days"][0]["nodes"][0]["title"], "New Hotel")
        self.assertNotEqual(result["decisionLog"]["executedAt"], "now")
        self.assertIn("T", result["decisionLog"]["executedAt"])

    def test_empty_proposal_cannot_be_persisted_or_executed(self):
        service = ProposalService()
        executor = ProposalExecutor()
        empty_proposal = {
            "proposal_id": "proposal-empty",
            "trip_id": "trip-1",
            "base_version": 1,
            "scope": "node",
            "title": "Empty",
            "summary": "No operations.",
            "operations": [],
        }

        with self.assertRaises(ValueError):
            service.persist_proposal(empty_proposal, current_trip_version=1)

        with self.assertRaises(ValueError):
            executor.execute(
                {"id": "trip-1", "version": 1, "days": []},
                {
                    "proposal_id": "proposal-empty",
                    "trip_id": "trip-1",
                    "base_version": 1,
                    "scope": "node",
                    "title": "Empty",
                    "summary": "No operations.",
                    "operations": [],
                    "status": "accepted",
                },
            )

    def test_proposal_without_operations_cannot_be_persisted(self):
        service = ProposalService()

        with self.assertRaises(ValueError):
            service.persist_proposal(
                {
                    "proposal_id": "proposal-missing-ops",
                    "trip_id": "trip-1",
                    "base_version": 1,
                    "scope": "node",
                    "title": "Missing operations",
                    "summary": "No operations field.",
                },
                current_trip_version=1,
            )

    def test_malformed_proposal_operation_is_rejected(self):
        with self.assertRaises(ValueError):
            TripProposal.model_validate(
                {
                    "proposal_id": "proposal-bad-op",
                    "trip_id": "trip-1",
                    "base_version": 1,
                    "scope": "node",
                    "title": "Bad operation",
                    "summary": "ReplaceNode has no replacement.",
                    "operations": [{"type": "ReplaceNode", "day_id": "day-1", "node_id": "node-1"}],
                    "status": "accepted",
                },
            )

    def test_executor_ignores_unsafe_llm_patch_fields(self):
        executor = ProposalExecutor()
        trip = {
            "id": "trip-1",
            "version": 1,
            "days": [{"id": "day-1", "nodes": [{"id": "node-1", "type": "activity", "title": "Old", "booked": True}]}],
        }
        proposal = {
            "proposal_id": "proposal-unsafe-patch",
            "trip_id": "trip-1",
            "base_version": 1,
            "scope": "trip",
            "title": "Unsafe patch",
            "summary": "Patch includes identity fields.",
            "operations": [
                {
                    "type": "UpdateNode",
                    "day_id": "day-1",
                    "node_id": "node-1",
                    "patch": {"id": "changed", "type": "hotel", "booked": False, "title": "Safer Title"},
                },
            ],
            "status": "accepted",
        }

        updated = executor.execute(trip, proposal)

        node = updated["trip"]["days"][0]["nodes"][0]
        self.assertEqual(node["id"], "node-1")
        self.assertEqual(node["type"], "activity")
        self.assertEqual(node["booked"], True)
        self.assertEqual(node["title"], "Safer Title")

    def test_executor_rejects_operation_that_matches_no_node(self):
        executor = ProposalExecutor()

        with self.assertRaises(ValueError):
            executor.execute(
                {"id": "trip-1", "version": 1, "days": [{"id": "day-1", "nodes": []}]},
                {
                    "proposal_id": "proposal-missing-node",
                    "trip_id": "trip-1",
                    "base_version": 1,
                    "scope": "node",
                    "title": "Missing node",
                    "summary": "Target node is gone.",
                    "operations": [
                        {
                            "type": "ReplaceNode",
                            "day_id": "day-1",
                            "node_id": "node-1",
                            "replacement": {"title": "New Hotel"},
                        },
                    ],
                    "status": "accepted",
                },
            )

    def test_replace_node_merges_replacement_over_existing_node(self):
        service = ProposalService()
        executor = ProposalExecutor()
        trip = {
            "id": "trip-1",
            "version": 1,
            "days": [
                {
                    "id": "day-1",
                    "nodes": [
                        {
                            "id": "node-1",
                            "type": "hotel",
                            "time": "15:00",
                            "location": "Hakata",
                            "title": "Old Hotel",
                        },
                    ],
                },
            ],
        }
        proposal = {
            "proposal_id": "proposal-merge",
            "trip_id": "trip-1",
            "base_version": 1,
            "scope": "node",
            "title": "Replace hotel",
            "summary": "Use a different hotel.",
            "operations": [
                {
                    "type": "ReplaceNode",
                    "day_id": "day-1",
                    "node_id": "node-1",
                    "replacement": {"title": "New Hotel"},
                },
            ],
        }

        stored = service.persist_proposal(proposal, current_trip_version=1)
        accepted = service.update_proposal_status(stored.proposal_id, "accepted")
        result = executor.execute(trip, accepted)
        node = result["trip"]["days"][0]["nodes"][0]

        self.assertEqual(node["title"], "New Hotel")
        self.assertEqual(node["id"], "node-1")
        self.assertEqual(node["type"], "hotel")
        self.assertEqual(node["time"], "15:00")
        self.assertEqual(node["location"], "Hakata")

    def test_proposal_response_includes_frontend_camel_case_contract(self):
        advisor = TravelAdvisor(graph=TripPlanningGraph(provider=FakeProvider()))
        trip = {
            "id": "trip-1",
            "version": 1,
            "days": [{"id": "day-1", "nodes": [{"id": "node-1", "type": "hotel", "title": "Old Hotel"}]}],
        }

        result = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="Replan this day and update this hotel",
            trip=trip,
            intent={
                "kind": "replan",
                "scope": "day",
                "affected_day_ids": ["day-1"],
                "affected_node_ids": ["node-1"],
            },
        )

        frontend = result["frontendProposal"]
        self.assertIn("proposalId", frontend)
        self.assertIn("baseVersion", frontend)
        self.assertIn("affectedDayIds", frontend["impact"])
        self.assertIn("dayId", frontend["operations"][0])

    def test_travel_advisor_accepts_frontend_camel_case_intent(self):
        advisor = TravelAdvisor(graph=TripPlanningGraph(provider=FakeProvider()))
        trip = {
            "id": "trip-1",
            "version": 1,
            "days": [
                {"id": "day-1", "nodes": [{"id": "node-1", "type": "hotel", "title": "Old Hotel"}]},
                {"id": "day-2", "nodes": [{"id": "node-2", "type": "activity", "title": "Old Activity"}]},
            ],
        }

        result = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="This touches two days",
            trip=trip,
            intent={
                "kind": "replan",
                "scope": "trip",
                "affectedDayIds": ["day-1", "day-2"],
                "affectedNodeIds": ["node-1", "node-2"],
                "canCloseLocally": False,
            },
        )

        self.assertEqual(result["kind"], "proposal")
        self.assertEqual(result["routing"]["decision"], "graph_replan")
        self.assertEqual(result["routing"]["affected_day_ids"], ["day-1", "day-2"])
        self.assertEqual(result["routing"]["affected_node_ids"], ["node-1", "node-2"])
        self.assertEqual(result["proposal"]["impact"]["affected_day_ids"], ["day-1", "day-2"])

    def test_explicit_initial_plan_mode_ignores_existing_trip_for_new_plan(self):
        advisor = TravelAdvisor(graph=TripPlanningGraph(provider=FakeProvider()))
        trip = {
            "id": "trip-1",
            "version": 1,
            "days": [{"id": "day-1", "nodes": [{"id": "node-1", "type": "hotel", "title": "Old Hotel"}]}],
        }

        result = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="Plan a fresh 3-day Fukuoka trip",
            trip=trip,
            intent={"kind": "initial_plan", "mode": "initial_plan"},
        )

        self.assertEqual(result["kind"], "trip_board")
        self.assertEqual(result["trip"]["source_recommendation_id"], "plan-1")

    def test_application_services_start_initial_plan_run(self):
        services = AgentApplicationServices(graph=TripPlanningGraph(provider=FakeProvider()))

        result = services.start_initial_plan_run(
            {
                "user_id": "user-1",
                "conversation_id": "conversation-1",
                "user_message": "帮我规划一个福冈三日游，想吃好吃的，也想安排一天周边游",
            },
        )

        self.assertEqual(result["kind"], "agent_run_accepted")
        self.assertEqual(result["output"]["kind"], "trip_board")
        self.assertEqual(result["output"]["trip"]["source_recommendation_id"], "plan-1")

    def test_application_services_lightweight_answer_uses_graph_provider(self):
        provider = AnswerProvider()
        services = AgentApplicationServices(graph=TripPlanningGraph(provider=provider))
        trip = {
            "id": "trip-1",
            "version": 1,
            "days": [{"id": "day-1", "nodes": [{"id": "node-1", "type": "hotel", "title": "Hotel"}]}],
        }

        result = services.handle_discussion_turn(
            {
                "user_id": "user-1",
                "discussion_id": "discussion-1",
                "user_message": "Is this hotel convenient?",
                "trip": trip,
                "intent": {"kind": "ask"},
            },
        )

        self.assertEqual(result["output"]["kind"], "answer")
        self.assertEqual(result["output"]["text"], "model says this is a good lightweight answer")
        self.assertEqual(len(provider.answer_calls), 1)

    def test_application_services_discussion_turn_returns_graph_replan_proposal(self):
        services = AgentApplicationServices(graph=TripPlanningGraph(provider=FakeProvider()))
        trip = {
            "id": "trip-1",
            "version": 1,
            "days": [{"id": "day-1", "nodes": [{"id": "node-1", "type": "activity", "title": "Old Activity"}]}],
        }

        result = services.handle_discussion_turn(
            {
                "user_id": "user-1",
                "discussion_id": "discussion-1",
                "user_message": "第二天会影响整体节奏，帮我重排一下",
                "trip": trip,
                "intent": {
                    "kind": "replan",
                    "scope": "trip",
                    "affected_day_ids": ["day-1", "day-2"],
                    "affected_node_ids": ["node-1"],
                    "can_close_locally": False,
                },
            },
        )

        self.assertEqual(result["output"]["kind"], "proposal")
        self.assertEqual(result["output"]["proposal"]["status"], "pending")
        self.assertEqual(result["output"]["proposal"]["impact"]["affected_day_ids"], ["day-1", "day-2"])
        operation = result["output"]["proposal"]["operations"][0]
        self.assertIn("Adjusted Old Activity", operation["patch"]["title"])
        self.assertNotIn("Graph replanned this node", json.dumps(operation, ensure_ascii=False))

    def test_graph_replan_uses_affected_node_ids_when_building_operations(self):
        services = AgentApplicationServices(graph=TripPlanningGraph(provider=FakeProvider()))
        trip = {
            "id": "trip-1",
            "version": 1,
            "days": [
                {
                    "id": "day-1",
                    "nodes": [
                        {"id": "node-1", "type": "activity", "title": "Keep This"},
                        {"id": "node-2", "type": "activity", "title": "Change This"},
                    ],
                },
            ],
        }

        result = services.handle_discussion_turn(
            {
                "user_id": "user-1",
                "discussion_id": "discussion-1",
                "user_message": "Please update the second activity",
                "trip": trip,
                "intent": {
                    "kind": "replan",
                    "scope": "trip",
                    "affected_day_ids": ["day-1"],
                    "affected_node_ids": ["node-2"],
                    "can_close_locally": False,
                },
            },
        )

        operations = result["output"]["proposal"]["operations"]
        self.assertEqual([operation["node_id"] for operation in operations], ["node-2"])
        self.assertEqual(operations[0]["patch"]["title"], "Adjusted Change This")

    def test_graph_replan_uses_node_id_fallback_and_skips_initial_research(self):
        provider = ReplanRecordingProvider()
        services = AgentApplicationServices(graph=TripPlanningGraph(provider=provider))
        trip = {
            "id": "trip-1",
            "version": 1,
            "days": [{"id": "day-1", "nodes": [{"id": "node-1", "type": "activity", "title": "Change This"}]}],
        }

        result = services.handle_discussion_turn(
            {
                "user_id": "user-1",
                "discussion_id": "discussion-1",
                "user_message": "Please update this node",
                "trip": trip,
                "intent": {
                    "kind": "replan",
                    "scope": "trip",
                    "affected_day_ids": ["day-1"],
                    "node_id": "node-1",
                    "can_close_locally": False,
                },
            },
        )

        self.assertEqual(result["output"]["kind"], "proposal")
        self.assertEqual(provider.research_calls, [])
        self.assertIn('"affected_node_ids": ["node-1"]', provider.replan_prompts[0])
        self.assertIn('"_capability_plan"', provider.replan_prompts[0])
        self.assertIn('"required": ["experience"]', provider.replan_prompts[0])

    def test_graph_replan_rejects_operations_outside_target_nodes(self):
        services = AgentApplicationServices(graph=TripPlanningGraph(provider=ReplanWrongTargetProvider()))
        trip = {
            "id": "trip-1",
            "version": 1,
            "days": [{"id": "day-1", "nodes": [{"id": "node-1", "type": "activity", "title": "Change This"}]}],
        }

        result = services.handle_discussion_turn(
            {
                "user_id": "user-1",
                "discussion_id": "discussion-1",
                "user_message": "Please rebalance this node",
                "trip": trip,
                "intent": {
                    "kind": "replan",
                    "scope": "trip",
                    "affected_day_ids": ["day-1"],
                    "affected_node_ids": ["node-1"],
                    "can_close_locally": False,
                },
            },
        )

        self.assertEqual(result["output"]["kind"], "answer")
        self.assertEqual(result["output"]["fallback"]["graph_error"]["error_code"], "ValueError")

    def test_graph_replan_provider_failure_returns_graph_error_instead_of_template_patch(self):
        services = AgentApplicationServices(graph=TripPlanningGraph(provider=FailingReplanProposalProvider()))
        trip = {
            "id": "trip-1",
            "version": 1,
            "days": [{"id": "day-1", "nodes": [{"id": "node-1", "type": "activity", "title": "Old Activity"}]}],
        }

        result = services.handle_discussion_turn(
            {
                "user_id": "user-1",
                "discussion_id": "discussion-1",
                "user_message": "Please rebalance this day",
                "trip": trip,
                "intent": {
                    "kind": "replan",
                    "scope": "trip",
                    "affected_day_ids": ["day-1"],
                    "affected_node_ids": ["node-1"],
                    "can_close_locally": False,
                },
            },
        )

        self.assertEqual(result["output"]["kind"], "answer")
        self.assertEqual(result["output"]["fallback"]["decision"], "ask_retry_later")
        self.assertEqual(result["output"]["fallback"]["graph_error"]["error_code"], "timeout_error")

    def test_graph_day_replan_without_target_node_returns_fallback_instead_of_first_node_patch(self):
        services = AgentApplicationServices(graph=TripPlanningGraph(provider=FakeProvider()))
        trip = {
            "id": "trip-1",
            "version": 1,
            "days": [
                {
                    "id": "day-1",
                    "nodes": [
                        {"id": "node-1", "type": "hotel", "title": "Hotel"},
                        {"id": "node-2", "type": "activity", "title": "Museum"},
                    ],
                }
            ],
        }

        result = services.handle_discussion_turn(
            {
                "user_id": "user-1",
                "discussion_id": "discussion-1",
                "user_message": "Please make day one less rushed",
                "trip": trip,
                "intent": {
                    "kind": "replan",
                    "scope": "day",
                    "affected_day_ids": ["day-1"],
                    "can_close_locally": False,
                },
            },
        )

        self.assertEqual(result["output"]["kind"], "answer")
        self.assertEqual(result["output"]["fallback"]["graph_error"]["error_code"], "replan_requires_target_nodes")

    def test_graph_replan_requires_provider_title_and_summary(self):
        services = AgentApplicationServices(graph=TripPlanningGraph(provider=IncompleteReplanProposalProvider()))
        trip = {
            "id": "trip-1",
            "version": 1,
            "days": [{"id": "day-1", "nodes": [{"id": "node-1", "type": "activity", "title": "Old Activity"}]}],
        }

        result = services.handle_discussion_turn(
            {
                "user_id": "user-1",
                "discussion_id": "discussion-1",
                "user_message": "Please rebalance this node",
                "trip": trip,
                "intent": {
                    "kind": "replan",
                    "scope": "trip",
                    "affected_day_ids": ["day-1"],
                    "affected_node_ids": ["node-1"],
                    "can_close_locally": False,
                },
            },
        )

        self.assertEqual(result["output"]["kind"], "answer")
        self.assertEqual(result["output"]["fallback"]["graph_error"]["error_code"], "ValueError")

    def test_free_text_replace_without_trip_stays_in_lightweight_consultation(self):
        advisor = TravelAdvisor(graph=TripPlanningGraph(provider=FakeProvider()))

        result = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="Replace this hotel",
            intent={"kind": "replace_node", "node_id": "node-1"},
        )

        self.assertEqual(result["kind"], "answer")
        self.assertEqual(result["routing"]["decision"], "lightweight_research")
        self.assertEqual(result["fallback"]["decision"], "fallback_to_answer")

    def test_free_text_replace_with_invalid_node_stays_in_lightweight_consultation(self):
        advisor = TravelAdvisor(graph=TripPlanningGraph(provider=FakeProvider()))
        trip = {
            "id": "trip-1",
            "version": 1,
            "days": [{"id": "day-1", "nodes": [{"id": "node-1", "type": "hotel", "title": "Old Hotel"}]}],
        }

        result = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="Replace missing node",
            trip=trip,
            intent={"kind": "replace_node", "node_id": "missing-node"},
        )

        self.assertEqual(result["kind"], "answer")
        self.assertEqual(result["routing"]["decision"], "lightweight_research")
        self.assertEqual(result["fallback"]["decision"], "fallback_to_answer")

    def test_free_text_replace_answer_is_not_demo_specific_proposal(self):
        advisor = TravelAdvisor(graph=TripPlanningGraph(provider=AnswerProvider()))
        trip = {
            "id": "trip-1",
            "version": 1,
            "days": [{"id": "day-1", "nodes": [{"id": "node-1", "type": "hotel", "title": "Kyoto Ryokan"}]}],
        }

        result = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="Replace this hotel",
            trip=trip,
            intent={"kind": "replace_hotel", "node_id": "node-1"},
        )

        self.assertEqual(result["kind"], "answer")
        self.assertEqual(result["routing"]["decision"], "lightweight_research")
        self.assertNotIn("frontendProposal", result)
        self.assertNotIn("proposal", result)

    def test_graph_replan_without_matching_operations_returns_fallback(self):
        services = AgentApplicationServices(graph=TripPlanningGraph(provider=FakeProvider()))
        trip = {
            "id": "trip-1",
            "version": 1,
            "days": [{"id": "day-1", "nodes": [{"id": "node-1", "type": "activity", "title": "Keep This"}]}],
        }

        result = services.handle_discussion_turn(
            {
                "user_id": "user-1",
                "discussion_id": "discussion-1",
                "user_message": "Please update a missing node",
                "trip": trip,
                "intent": {
                    "kind": "replan",
                    "scope": "trip",
                    "affected_day_ids": ["day-1"],
                    "affected_node_ids": ["missing-node"],
                    "can_close_locally": False,
                },
            },
        )

        self.assertEqual(result["output"]["kind"], "answer")
        self.assertEqual(result["output"]["fallback"]["decision"], "surface_error")
        self.assertEqual(result["output"]["fallback"]["graph_error"]["error_code"], "no_replan_operations")

    def test_advisor_contract_accepts_actual_proposal_response_shape(self):
        advisor = TravelAdvisor(graph=TripPlanningGraph(provider=FakeProvider()))
        trip = {
            "id": "trip-1",
            "version": 1,
            "days": [{"id": "day-1", "nodes": [{"id": "node-1", "type": "hotel", "title": "Old Hotel"}]}],
        }
        response = advisor.handle_request(
            user_id="user-1",
            conversation_id="conversation-1",
            user_message="Replan this day and update this hotel",
            trip=trip,
            intent={"kind": "replan", "scope": "day", "affected_day_ids": ["day-1"], "affected_node_ids": ["node-1"]},
        )

        parsed = ProposalResponse.model_validate(response)

        self.assertEqual(parsed.planning_brief["mode"], "day_replan")
        self.assertEqual(parsed.frontend_proposal["proposalId"], response["frontendProposal"]["proposalId"])

    def test_proposal_service_distinguishes_missing_and_invalid_status_transition(self):
        service = ProposalService()

        missing = service.try_update_proposal_status("missing", "accepted")

        proposal = {
            "proposal_id": "proposal-1",
            "trip_id": "trip-1",
            "base_version": 1,
            "scope": "node",
            "title": "Replace hotel",
            "summary": "Use a different hotel.",
            "operations": [
                {
                    "type": "ReplaceNode",
                    "day_id": "day-1",
                    "node_id": "node-1",
                    "replacement": {"title": "New Hotel"},
                },
            ],
        }
        stored = service.persist_proposal(proposal, current_trip_version=1)
        service.update_proposal_status(stored.proposal_id, "accepted")
        invalid = service.try_update_proposal_status(stored.proposal_id, "rejected")

        self.assertEqual(missing["ok"], False)
        self.assertEqual(missing["error"], "proposal_not_found")
        self.assertEqual(invalid["ok"], False)
        self.assertEqual(invalid["error"], "invalid_status_transition")

    def test_application_services_returns_structured_proposal_status_result(self):
        services = AgentApplicationServices(graph=TripPlanningGraph(provider=FakeProvider()))

        result = services.set_proposal_status("missing", "accepted")

        self.assertEqual(result["ok"], False)
        self.assertEqual(result["error"], "proposal_not_found")

    def test_actual_fallback_shapes_match_contract(self):
        lightweight = AdvisorFallbackDecision.model_validate(
            {
                "layer": "advisor",
                "decision": "fallback_to_answer",
                "message": "lightweight failed",
                "source": "lightweight",
                "retryable": True,
                "error_code": "timeout_error",
                "reason": "timeout",
            },
        )
        graph = AdvisorFallbackDecision.model_validate(
            {
                "layer": "advisor",
                "decision": "ask_retry_later",
                "message": "graph failed",
                "source": "graph",
                "retryable": True,
                "graph_error": {
                    "decision": "retry_later",
                    "retryable": True,
                    "message": "graph timeout",
                },
            },
        )

        self.assertEqual(lightweight.error_code, "timeout_error")
        self.assertEqual(graph.graph_error.decision, "retry_later")

    def test_qwen_provider_wraps_missing_config_as_provider_error(self):
        provider = QwenResearchProvider(api_key="", base_url="", model_name="")

        with self.assertRaises(LlmProviderError) as context:
            provider.generate_research(domain="stay", system_prompt="", user_prompt="")

        self.assertEqual(context.exception.code, "config_error")
        self.assertFalse(context.exception.retryable)

    def test_qwen_provider_clarification_uses_same_config_guard(self):
        provider = QwenResearchProvider(api_key="", base_url="", model_name="")

        with self.assertRaises(LlmProviderError) as context:
            provider.generate_clarification_decision(system_prompt="", user_prompt="")

        self.assertEqual(context.exception.code, "config_error")
        self.assertFalse(context.exception.retryable)

    def test_qwen_provider_new_structured_methods_use_same_config_guard(self):
        provider = QwenResearchProvider(api_key="", base_url="", model_name="")

        for method_name in ["generate_replan_routing_decision", "generate_specialist_selection", "generate_replan_proposal"]:
            with self.subTest(method_name=method_name):
                with self.assertRaises(LlmProviderError) as context:
                    getattr(provider, method_name)(system_prompt="", user_prompt="")
                self.assertEqual(context.exception.code, "config_error")
                self.assertFalse(context.exception.retryable)


class ManualAgentPlaygroundTest(unittest.TestCase):
    def test_parse_args_keeps_single_rounds_entrypoint(self):
        with patch("sys.argv", ["manual_agent_playground.py"]):
            args = manual_agent_playground.parse_args()

        self.assertFalse(args.self_check)
        self.assertFalse(hasattr(args, "chat"))

    def test_build_context_message_includes_latest_recommendations_and_trip(self):
        message = manual_agent_playground.build_context_message(
            message="你觉得第二天会不会太赶？",
            history=[{"role": "user", "content": "帮我规划福冈三日游"}],
            current_trip=manual_agent_playground.sample_trip(),
            latest_recommendation_set={
                "recommendations": [
                    {
                        "title": "Hakata base with Dazaifu day trip",
                        "summary": "Food-focused plan.",
                    },
                ],
            },
        )

        self.assertIn("Conversation history", message)
        self.assertIn("Current trip summary", message)
        self.assertIn("day-2", message)
        self.assertIn("Latest recommendation summary", message)
        self.assertIn("Hakata base with Dazaifu day trip", message)

    def test_round_one_stores_current_trip_board(self):
        advisor = SequencedAdvisor(
            [
                {
                    "kind": "trip_board",
                    "routing": {"decision": "graph_replan"},
                    "trip": {"id": "trip-plan-a", "version": 1, "title": "Plan A", "days": []},
                    "sourceRecommendationSet": {
                        "recommendations": [
                            {"title": "Plan A", "theme": "Food", "summary": "Summary A"},
                        ],
                    },
                },
            ],
        )
        session = manual_agent_playground.ManualTestSession()

        result = manual_agent_playground.run_round_initial_plan(advisor, session, "Plan a three-day Fukuoka food trip")

        self.assertEqual(result["kind"], "trip_board")
        self.assertEqual(session.current_trip["id"], "trip-plan-a")
        self.assertEqual(session.latest_recommendation_set["recommendations"][0]["title"], "Plan A")
        self.assertEqual(session.history[-1]["role"], "assistant")
        self.assertEqual(advisor.calls[0]["intent"]["kind"], "initial_plan")

    def test_round_two_followup_uses_ask_intent_and_augmented_context(self):
        advisor = SequencedAdvisor([{"kind": "answer", "routing": {"decision": "direct_answer"}, "text": "Day 2 is relaxed."}])
        session = manual_agent_playground.ManualTestSession(
            latest_recommendation_set={"recommendations": [{"title": "Plan A", "summary": "Summary A"}]},
        )
        session.history.append({"role": "user", "content": "帮我规划一个福冈三日游"})

        manual_agent_playground.run_round_context_followup(advisor, session, "你觉得第二天会不会太赶？")

        call = advisor.calls[0]
        self.assertEqual(call["intent"]["kind"], "ask")
        self.assertIn("Plan A", call["user_message"])
        self.assertIsNone(call["trip"])

    def test_select_recommendation_converts_it_to_current_trip(self):
        session = manual_agent_playground.ManualTestSession(
            latest_recommendation_set={
                "recommendations": [
                    {
                        "id": "plan-1",
                        "title": "Plan A",
                        "day_plans": [
                            {
                                "day": 1,
                                "title": "Arrival",
                                "blocks": [
                                    {
                                        "time_of_day": "evening",
                                        "type": "meal",
                                        "title": "Ramen dinner",
                                        "location": "Hakata",
                                        "duration": "1 hour",
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
        )

        trip = manual_agent_playground.select_recommendation_as_current_trip(session, 1)

        self.assertEqual(session.current_trip["days"][0]["id"], "day-1")
        self.assertEqual(trip["days"][0]["nodes"][0]["title"], "Ramen dinner")

    def test_round_four_generates_replan_proposal_against_current_trip(self):
        advisor = SequencedAdvisor([{"kind": "proposal", "proposal": {"proposal_id": "proposal-1"}, "routing": {}}])
        session = manual_agent_playground.ManualTestSession(current_trip=manual_agent_playground.sample_trip())

        result = manual_agent_playground.run_round_proposal(advisor, session, "第二天和第三天都有点赶，帮我重新平衡一下")

        self.assertEqual(result["kind"], "proposal")
        self.assertEqual(session.latest_proposal_id, "proposal-1")
        self.assertEqual(advisor.calls[0]["intent"]["kind"], "replan")
        self.assertEqual(advisor.calls[0]["intent"]["affected_day_ids"], ["day-2", "day-3"])

    def test_round_five_accepts_latest_proposal(self):
        class ExecutingAdvisor:
            def __init__(self):
                self.calls = []

            def execute_proposal(self, **kwargs):
                self.calls.append(kwargs)
                return {"kind": "execution", "trip": {"id": "trip-1", "version": 2}, "decisionLog": {"proposalId": kwargs["proposal_id"]}}

        advisor = ExecutingAdvisor()
        session = manual_agent_playground.ManualTestSession(
            current_trip={"id": "trip-1", "version": 1, "days": []},
            latest_proposal_id="proposal-1",
        )

        result = manual_agent_playground.run_round_accept(advisor, session)

        self.assertEqual(result["kind"], "execution")
        self.assertEqual(session.current_trip["version"], 2)
        self.assertEqual(advisor.calls[0]["proposal_id"], "proposal-1")

    def test_round_five_does_not_execute_when_acceptance_fails(self):
        class RejectingProposalService:
            def update_proposal_status(self, proposal_id, status):
                return None

        class ExecutingAdvisor:
            def __init__(self):
                self.proposal_service = RejectingProposalService()
                self.calls = []

            def execute_proposal(self, **kwargs):
                self.calls.append(kwargs)
                return {"kind": "execution"}

        advisor = ExecutingAdvisor()
        session = manual_agent_playground.ManualTestSession(
            current_trip={"id": "trip-1", "version": 1, "days": []},
            latest_proposal_id="proposal-1",
        )

        result = manual_agent_playground.run_round_accept(advisor, session)

        self.assertEqual(result["kind"], "manual_error")
        self.assertEqual(advisor.calls, [])

    def test_input_or_default_can_return_to_menu(self):
        with patch("builtins.input", return_value="b"):
            with patch("sys.stdout", new=io.StringIO()):
                with self.assertRaises(manual_agent_playground.BackToMenu):
                    manual_agent_playground.input_or_default("Travel request", "default request")

    def test_input_or_default_uses_default_on_blank_input(self):
        with patch("builtins.input", return_value=""):
            with patch("sys.stdout", new=io.StringIO()):
                self.assertEqual(
                    manual_agent_playground.input_or_default("Travel request", "default request"),
                    "default request",
                )

    def test_main_exits_cleanly_on_keyboard_interrupt(self):
        class Args:
            self_check = False

        with patch.object(manual_agent_playground, "parse_args", return_value=Args()):
            with patch.object(manual_agent_playground, "load_dotenv"):
                with patch.object(manual_agent_playground, "TravelAdvisor", return_value=object()):
                    with patch("builtins.input", side_effect=KeyboardInterrupt):
                        with patch("sys.stdout", new=io.StringIO()) as stdout:
                            manual_agent_playground.main()

        self.assertIn("Interrupted", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
