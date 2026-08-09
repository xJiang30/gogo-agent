from typing import Any

from agents import Agent, GuardrailFunctionOutput, RunContextWrapper, output_guardrail

from app.schemas.intake import IntakeResponse

MUTATION_CLAIM_PATTERNS = (
    "已应用",
    "已经应用",
    "应用到 Trip Board",
    "已修改",
    "已经修改",
    "修改好了",
    "已保存",
    "已经保存",
    "已预订",
    "已经预订",
    "booked",
    "reserved",
    "applied",
    "saved",
)


def validate_intake_output_is_proposal_safe(
    output: IntakeResponse,
) -> GuardrailFunctionOutput:
    message = output.assistant_message.lower()
    matched_pattern = next(
        (
            pattern
            for pattern in MUTATION_CLAIM_PATTERNS
            if pattern.lower() in message
        ),
        None,
    )

    return GuardrailFunctionOutput(
        output_info={
            "reason": (
                "proposal-only output"
                if matched_pattern is None
                else f"proposal-only violation: {matched_pattern}"
            )
        },
        tripwire_triggered=matched_pattern is not None,
    )


@output_guardrail
def proposal_only_output_guardrail(
    ctx: RunContextWrapper[Any],
    agent: Agent[Any],
    output: Any,
) -> GuardrailFunctionOutput:
    if isinstance(output, IntakeResponse):
        return validate_intake_output_is_proposal_safe(output)

    return GuardrailFunctionOutput(
        output_info={"reason": "unsupported output type for proposal-only guardrail"},
        tripwire_triggered=True,
    )
