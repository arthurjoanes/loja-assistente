"""Optional evaluation hooks; only an explicit allowlist of provider metadata leaves the adapter."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass
class ProviderTrace:
    call_id: str
    model_requested: str
    prompt_sha256: str
    schema_sha256: str
    reasoning_effort: str | None = None
    status: str = "started"
    provider_request_id: str | None = None
    response_id: str | None = None
    model_returned: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    duration_ms: int = 0
    attempts: int = 1


@dataclass(frozen=True)
class EvaluationHooks:
    # Reserve before touching the network; failures and unknown usage still consume the reservation.
    reserve: Callable[[str, int, int], None]
    record: Callable[[ProviderTrace], None]


_hooks: ContextVar[EvaluationHooks | None] = ContextVar("loja_evaluation_hooks", default=None)


@contextmanager
def observe_provider(hooks: EvaluationHooks) -> Iterator[None]:
    token = _hooks.set(hooks)
    try:
        yield
    finally:
        _hooks.reset(token)


def evaluation_hooks() -> EvaluationHooks | None:
    return _hooks.get()
