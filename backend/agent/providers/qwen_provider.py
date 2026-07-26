import json
import os
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import quote

from .errors import LlmProviderError


class QwenResearchProvider:
    """OpenAI-compatible DashScope client used by the Python graph."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model_name: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.base_url = (base_url or os.getenv("LLM_API_BASE") or "").rstrip("/")
        self.model_name = model_name or os.getenv("LLM_MODEL_NAME")
        self.timeout_seconds = timeout_seconds or float(os.getenv("LLM_TIMEOUT_MS", "60000")) / 1000

    def generate_research(self, *, domain: str, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        self._ensure_configured()
        content = self._chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LlmProviderError(
                code="provider_response_error",
                message="Provider response was not valid research JSON",
                retryable=False,
                details=content,
            ) from exc
        parsed.setdefault("domain", domain)
        return parsed

    def generate_answer(self, *, system_prompt: str, user_prompt: str) -> str:
        self._ensure_configured()
        return self._chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        ).strip()

    def generate_planning_brief(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        self._ensure_configured()
        content = self._chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LlmProviderError(
                code="provider_response_error",
                message="Provider response was not valid PlanningBrief JSON",
                retryable=False,
                details=content,
            ) from exc

    def generate_clarification_decision(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        self._ensure_configured()
        content = self._chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LlmProviderError(
                code="provider_response_error",
                message="Provider response was not valid ClarificationDecision JSON",
                retryable=False,
                details=content,
            ) from exc

    def generate_replan_routing_decision(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        return self._generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            error_message="Provider response was not valid ReplanRoutingDecision JSON",
        )

    def generate_specialist_selection(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        return self._generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            error_message="Provider response was not valid SpecialistSelection JSON",
        )

    def generate_recommendations(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        self._ensure_configured()
        content = self._chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LlmProviderError(
                code="provider_response_error",
                message="Provider response was not valid recommendation planner JSON",
                retryable=False,
                details=content,
            ) from exc

    def generate_replan_proposal(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        self._ensure_configured()
        content = self._chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LlmProviderError(
                code="provider_response_error",
                message="Provider response was not valid replan proposal JSON",
                retryable=False,
                details=content,
            ) from exc

    def _generate_json(self, *, system_prompt: str, user_prompt: str, error_message: str) -> dict[str, Any]:
        self._ensure_configured()
        content = self._chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LlmProviderError(
                code="provider_response_error",
                message=error_message,
                retryable=False,
                details=content,
            ) from exc

    def get_weather_context(self, *, planning_brief) -> dict[str, Any] | None:
        destination = planning_brief.destination_candidates[0] if planning_brief.destination_candidates else None
        if not destination:
            return None
        try:
            location = self._open_meteo_geocode(destination)
            if not location:
                return {"source": "open_meteo", "destination": destination, "warnings": ["Weather location was not found."]}
            forecast = self._open_meteo_forecast(location["latitude"], location["longitude"])
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, TypeError) as exc:
            return {
                "source": "open_meteo",
                "destination": destination,
                "warnings": [f"Weather API unavailable: {type(exc).__name__}"],
            }
        return {
            "source": "open_meteo",
            "destination": destination,
            "location": location,
            "daily": forecast,
            "warnings": [],
        }

    def get_stay_context(self, *, planning_brief) -> dict[str, Any] | None:
        return None

    def get_mobility_context(self, *, planning_brief) -> dict[str, Any] | None:
        return None

    def _open_meteo_geocode(self, destination: str) -> dict[str, Any] | None:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={quote(destination)}&count=1&language=en&format=json"
        with urllib.request.urlopen(url, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        results = payload.get("results") or []
        if not results:
            return None
        first = results[0]
        return {
            "name": first.get("name"),
            "country": first.get("country"),
            "latitude": first["latitude"],
            "longitude": first["longitude"],
        }

    def _open_meteo_forecast(self, latitude: float, longitude: float) -> list[dict[str, Any]]:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={latitude}&longitude={longitude}"
            "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
            "&forecast_days=7&timezone=auto"
        )
        with urllib.request.urlopen(url, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        daily = payload.get("daily", {})
        dates = daily.get("time", [])
        return [
            {
                "date": date,
                "weather_code": get_index(daily.get("weather_code"), index),
                "temperature_max_c": get_index(daily.get("temperature_2m_max"), index),
                "temperature_min_c": get_index(daily.get("temperature_2m_min"), index),
                "precipitation_probability_max": get_index(daily.get("precipitation_probability_max"), index),
            }
            for index, date in enumerate(dates)
        ]

    def _ensure_configured(self) -> None:
        if not self.api_key or not self.base_url or not self.model_name:
            raise LlmProviderError(
                code="config_error",
                message="Missing LLM_API_KEY, LLM_API_BASE, or LLM_MODEL_NAME",
                retryable=False,
            )

    def _chat_completion(self, *, messages: list[dict[str, str]], response_format: dict[str, str] | None = None) -> str:
        payload = {
            "model": self.model_name,
            "messages": messages,
        }
        if response_format:
            payload["response_format"] = response_format
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise LlmProviderError(
                code="provider_http_error",
                message=f"Provider HTTP error {exc.code}",
                retryable=exc.code == 429 or exc.code >= 500,
                status=exc.code,
                details=details,
            ) from exc
        except TimeoutError as exc:
            raise LlmProviderError(
                code="timeout_error",
                message="Provider request timed out",
                retryable=True,
            ) from exc
        except urllib.error.URLError as exc:
            raise LlmProviderError(
                code="network_error",
                message="Provider network error",
                retryable=True,
                details=str(exc.reason),
            ) from exc

        try:
            content = json.loads(body)["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise LlmProviderError(
                code="provider_response_error",
                message="Provider response was not valid OpenAI-compatible JSON",
                retryable=False,
                details=body,
            ) from exc
        return content


def get_index(items, index):
    if not isinstance(items, list) or index >= len(items):
        return None
    return items[index]
