from backend.agent.contracts.errors import GraphErrorEnvelope
from backend.agent.contracts.research_outcome import ResearchOutcome
from backend.agent.providers.failure_policy import classify_provider_failure


def run_research_step(*, domain: str, research_call):
    try:
        result = research_call()
        if not result.evidence or (result.confidence or 0) < 0.5:
            return {
                "outcome": ResearchOutcome(
                    domain=domain,
                    status="degraded",
                    result=result,
                    reason="low_confidence_or_missing_evidence",
                ),
                "graph_error": None,
            }

        return {
            "outcome": ResearchOutcome(domain=domain, status="success", result=result),
            "graph_error": None,
        }
    except Exception as error:
        failure = classify_provider_failure(error)
        decision = "fail_run" if failure["action"] == "fail_fast" else "retry_later"
        return {
            "outcome": ResearchOutcome(
                domain=domain,
                status="failed",
                reason=failure["reason"],
                retryable=failure["retryable"],
                error_code=failure["error_code"],
            ),
            "graph_error": GraphErrorEnvelope(
                decision=decision,
                retryable=failure["retryable"],
                error_code=failure["error_code"],
                failed_domains=[domain],
                message=failure["reason"],
                provider_status=getattr(error, "status", None),
            ),
        }
