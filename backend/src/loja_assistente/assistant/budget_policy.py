"""Operational allowance, not prices, tokenization guarantees or an invoice."""

from dataclasses import dataclass

MAX_COUNTER = 2**63 - 1


class BudgetRejected(RuntimeError):
    """A fail-closed refusal with a safe user-facing message."""


def integer(value: int, *, positive: bool = False) -> None:
    if type(value) is not int or not (int(positive) <= value <= MAX_COUNTER):
        raise BudgetRejected("Limite ou uso operacional inválido.")


@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int
    total_tokens: int


def known_usage(
    input_tokens: int | None, output_tokens: int | None, total_tokens: int | None
) -> Usage | None:
    values = (input_tokens, output_tokens, total_tokens)
    if any(type(value) is not int or not 0 <= value <= MAX_COUNTER for value in values):
        return None
    if input_tokens + output_tokens != total_tokens:  # type: ignore[operator]
        return None
    return Usage(input_tokens, output_tokens, total_tokens)  # type: ignore[arg-type]


def observed_excess(
    input_tokens: int | None,
    output_tokens: int | None,
    total_tokens: int | None,
    reserved_input: int,
    reserved_output: int,
) -> bool:
    return any(
        type(actual) is int and actual > limit
        for actual, limit in (
            (input_tokens, reserved_input),
            (output_tokens, reserved_output),
            (total_tokens, reserved_input + reserved_output),
        )
    )


def admit(
    *,
    blocked: bool,
    calls: int,
    input_units: int,
    output_units: int,
    calls_limit: int,
    input_limit: int,
    output_limit: int,
    reserve_input: int,
    reserve_output: int,
) -> None:
    integer(reserve_input, positive=True)
    integer(reserve_output, positive=True)
    if (
        blocked
        or calls + 1 > calls_limit
        or input_units + reserve_input > input_limit
        or output_units + reserve_output > output_limit
    ):
        raise BudgetRejected(
            "Limite de uso do modo LLM atingido. Selecione demo ou solicite revisão do uso autorizado."
        )
