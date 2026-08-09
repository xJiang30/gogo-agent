# Observability

Gogo Agent needs enough observability to understand why an agent produced a
recommendation without leaking user travel details by default.

## Trace Metadata

Agent runs should include lightweight metadata:

- `workflow_name`: the product workflow, such as `gogo-agent-intake`
- `group_id`: the active `session_id`
- `app_name`
- `app_env`
- `litellm_model`
- `session_id`

`app/providers/llm.py` owns this `RunConfig` setup so services do not duplicate
tracing behavior.

## Default Privacy Posture

Local development keeps trace export disabled by default:

```env
ENABLE_AGENT_TRACING=false
OPENAI_AGENTS_DONT_LOG_MODEL_DATA=1
OPENAI_AGENTS_DONT_LOG_TOOL_DATA=1
```

`trace_include_sensitive_data` is set to `False` in `RunConfig`. This avoids
recording full user messages, budgets, preferences, and tool payloads in traces
unless the team intentionally changes the setting for a controlled debugging
session.

## LiteLLM And Non-OpenAI Models

The backend routes models through `LitellmModel`, usually via LiteLLM Proxy.
Tracing export should therefore be treated separately from model routing.

If OpenAI tracing is enabled later, configure the OpenAI tracing credentials
explicitly and keep the LiteLLM provider credentials in the LiteLLM layer.
Avoid enabling hosted tracing implicitly just because a model provider key is
present.

## What To Inspect

Useful trace and log dimensions:

- session id and workflow name
- selected model alias
- tool calls and tool failures
- guardrail tripwires
- proposal creation
- proposal approval or rejection
- Trip Board apply success or failure

## Future Evals

Do not build a full eval suite until the Trip Board schema and UI loops are
more stable. Good first eval cases will be:

- intake asks only for necessary missing fields
- ready intake creates a Trip Board instead of more redundant questions
- proposals require user approval before mutation
- guardrails block unconfirmed mutation claims
- itinerary pacing stays light and avoids overstuffed days
