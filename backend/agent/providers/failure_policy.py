from .errors import LlmProviderError


def classify_provider_failure(error: Exception) -> dict:
    if isinstance(error, LlmProviderError):
        if error.code == "config_error":
            return {
                "action": "fail_fast",
                "reason": "provider_misconfigured",
                "retryable": False,
                "error_code": error.code,
            }
        if error.code in {"timeout_error", "network_error"}:
            return {
                "action": "retry",
                "reason": "provider_timeout",
                "retryable": True,
                "error_code": error.code,
            }
        if error.retryable:
            return {
                "action": "retry",
                "reason": "provider_transient_http",
                "retryable": True,
                "error_code": error.code,
            }
        return {
            "action": "fail",
            "reason": "provider_hard_failure",
            "retryable": False,
            "error_code": error.code,
        }

    return {
        "action": "fail",
        "reason": "provider_hard_failure",
        "retryable": False,
        "error_code": "unknown_error",
    }
