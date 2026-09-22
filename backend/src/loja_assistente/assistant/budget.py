"""PostgreSQL ledger with short, independent transactions and tenant-first locks.

Counters include known reported usage OR outstanding conservative reservations.
No clock reset, automatic expiry, network call under lock or unknown-usage release.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from loja_assistente.assistant.budget_policy import (
    MAX_COUNTER,
    BudgetRejected,
    admit,
    integer,
    known_usage,
    observed_excess,
)
from loja_assistente.assistant.provider_trace import ProviderTrace
from loja_assistente.database import SessionLocal
from loja_assistente.models import Organization, ProviderBudgetAccount, ProviderReservation, utcnow


def require(condition: bool, message: str) -> None:
    if not condition:
        raise BudgetRejected(message)


def observation(trace: ProviderTrace) -> dict[str, Any]:
    # Dataclass is an explicit allowlist; never store questions, bodies, keys or reasoning.
    value = asdict(trace)
    for name in ("provider_request_id", "response_id", "model_returned"):
        item = value[name]
        value[name] = item if isinstance(item, str) and item.strip() and len(item) <= 200 else None
    return value


class DurableBudget:
    def __init__(
        self,
        tenant_id: str,
        user_id: str,
        request_id: str,
        session_factory: Callable[[], Session] | None = None,
    ) -> None:
        require(
            all(
                isinstance(value, str) and 0 < len(value) <= 64
                for value in (tenant_id, user_id, request_id)
            ),
            "Identidade de orçamento inválida.",
        )
        self.tenant_id, self.user_id, self.request_id = tenant_id, user_id, request_id
        self.sessions = session_factory or SessionLocal

    @contextmanager
    def transaction(self) -> Iterator[Session]:
        try:
            with self.sessions() as session, session.begin():
                yield session
        except SQLAlchemyError as error:
            # A failed/ambiguous commit never permits the adapter to call the network.
            # If dispatch was already committed, its reservation remains held.
            raise BudgetRejected(
                "Não foi possível confirmar o limite de uso. Selecione demo e solicite revisão."
            ) from error

    def account(self, session: Session) -> ProviderBudgetAccount:
        account = session.scalar(
            select(ProviderBudgetAccount)
            .where(ProviderBudgetAccount.tenant_id == self.tenant_id)
            .with_for_update()
        )
        require(
            account is not None,
            "Modo LLM sem limite autorizado para esta organização. Selecione demo.",
        )
        assert account is not None
        return account

    def reservation(self, session: Session, call_id: str) -> ProviderReservation:
        require(
            isinstance(call_id, str) and 0 < len(call_id) <= 64, "Identidade da chamada inválida."
        )
        row = session.get(ProviderReservation, (self.tenant_id, call_id))
        require(row is not None, "Reserva não encontrada nesta organização.")
        assert row is not None
        return row

    def reserve(self, trace: ProviderTrace, input_units: int, output_units: int) -> None:
        require(
            0 < len(trace.call_id) <= 64 and 0 < len(trace.model_requested) <= 200,
            "Identidade do provedor inválida.",
        )
        integer(input_units, positive=True)
        integer(output_units, positive=True)
        with self.transaction() as session:
            account = self.account(session)
            existing = session.get(ProviderReservation, (self.tenant_id, trace.call_id))
            if existing is not None:
                require(
                    existing.state == "reserved"
                    and (
                        existing.reserved_input,
                        existing.reserved_output,
                        existing.request_id,
                        existing.user_id,
                        existing.model_requested,
                    )
                    == (
                        input_units,
                        output_units,
                        self.request_id,
                        self.user_id,
                        trace.model_requested,
                    ),
                    "Identidade da reserva já utilizada ou incompatível.",
                )
                return
            admit(
                blocked=account.blocked,
                calls=account.committed_calls,
                input_units=account.committed_input,
                output_units=account.committed_output,
                calls_limit=account.calls_limit,
                input_limit=account.input_limit,
                output_limit=account.output_limit,
                reserve_input=input_units,
                reserve_output=output_units,
            )
            account.committed_calls += 1
            account.committed_input += input_units
            account.committed_output += output_units
            account.updated_at = utcnow()
            session.add(
                ProviderReservation(
                    tenant_id=self.tenant_id,
                    call_id=trace.call_id,
                    request_id=self.request_id,
                    user_id=self.user_id,
                    model_requested=trace.model_requested,
                    reserved_input=input_units,
                    reserved_output=output_units,
                    state="reserved",
                )
            )

    def dispatch(self, call_id: str) -> None:
        with self.transaction() as session:
            account = self.account(session)
            row = self.reservation(session, call_id)
            require(
                not account.blocked, "Uso acima da reserva exige revisão antes de nova chamada."
            )
            require(
                row.state == "reserved", "Chamada já despachada ou encerrada; não repetir envio."
            )
            require(
                row.request_id == self.request_id and row.user_id == self.user_id,
                "Reserva pertence a outra solicitação.",
            )
            row.state = "dispatched"
            row.dispatched_at = utcnow()

    def cancel_before_dispatch(self, call_id: str) -> None:
        with self.transaction() as session:
            account = self.account(session)
            row = self.reservation(session, call_id)
            require(
                row.request_id == self.request_id and row.user_id == self.user_id,
                "Reserva pertence a outra solicitação.",
            )
            if row.state == "canceled":
                return
            require(
                row.state == "reserved" and row.dispatched_at is None,
                "Despacho confirmado ou incerto: a reserva não pode ser liberada.",
            )
            account.committed_calls -= 1
            account.committed_input -= row.reserved_input
            account.committed_output -= row.reserved_output
            account.updated_at = utcnow()
            row.state = "canceled"

    def record(self, trace: ProviderTrace) -> None:
        self.reconcile(trace, source="adapter", evidence_reference=None)

    def reconcile(
        self, trace: ProviderTrace, *, source: str, evidence_reference: str | None
    ) -> None:
        require(source in ("adapter", "operator_evidence"), "Origem da observação inválida.")
        current = observation(trace)
        if source == "operator_evidence":
            require(
                isinstance(evidence_reference, str)
                and bool(evidence_reference.strip())
                and len(evidence_reference or "") <= 500
                and bool(current["provider_request_id"] or current["response_id"]),
                "Reconciliação manual exige referência de evidência e ID do provedor.",
            )
        actual = known_usage(trace.input_tokens, trace.output_tokens, trace.total_tokens)
        if source == "operator_evidence":
            require(
                actual is not None,
                "Não informe zero ou uso estimado para liberar uma chamada incerta; apresente uso completo observado.",
            )
        with self.transaction() as session:
            account = self.account(session)
            row = self.reservation(session, trace.call_id)
            if source == "adapter":
                require(
                    row.request_id == self.request_id and row.user_id == self.user_id,
                    "Reserva pertence a outra solicitação.",
                )
            require(
                row.model_requested == trace.model_requested, "Modelo observado difere da reserva."
            )
            require(
                row.state in ("dispatched", "unknown", "reconciled")
                and row.dispatched_at is not None,
                "Sem despacho durável para esta observação.",
            )
            previous = row.observation or {}
            # A late complete observation can fill absent fields, not contradict prior evidence.
            for name in (
                "input_tokens",
                "output_tokens",
                "total_tokens",
                "provider_request_id",
                "response_id",
                "model_returned",
            ):
                if previous.get(name) is not None:
                    require(
                        current.get(name) == previous[name],
                        "Observação incompatível com a evidência já registrada.",
                    )
            if row.state == "reconciled":
                require(
                    actual is not None,
                    "Uma conciliação conhecida não pode voltar a uso desconhecido.",
                )
                return
            excess = observed_excess(
                trace.input_tokens,
                trace.output_tokens,
                trace.total_tokens,
                row.reserved_input,
                row.reserved_output,
            )
            if excess:
                account.blocked = True
                account.blocked_reason = "observed_usage_exceeded_reservation:" + trace.call_id
            if actual is not None:
                next_input = account.committed_input - row.reserved_input + actual.input_tokens
                next_output = account.committed_output - row.reserved_output + actual.output_tokens
                if next_input > MAX_COUNTER or next_output > MAX_COUNTER:
                    account.blocked = True
                    account.blocked_reason = "usage_counter_range_exceeded:" + trace.call_id
                    row.state = "unknown"
                else:
                    account.committed_input, account.committed_output = next_input, next_output
                    row.state = "reconciled"
            else:
                row.state = "unknown"
            row.observation = current
            row.observation_source = source
            row.evidence_reference = evidence_reference
            row.observed_at = account.updated_at = utcnow()

    def configure(self, calls_limit: int, input_limit: int, output_limit: int, reason: str) -> None:
        for value in (calls_limit, input_limit, output_limit):
            integer(value)
        require(
            0 < len(reason.strip()) <= 500,
            "Informe motivo de configuração entre 1 e 500 caracteres.",
        )
        with self.transaction() as session:
            require(
                session.get(Organization, self.tenant_id) is not None,
                "Organização confirmada não encontrada.",
            )
            account = session.scalar(
                select(ProviderBudgetAccount)
                .where(ProviderBudgetAccount.tenant_id == self.tenant_id)
                .with_for_update()
            )
            if account is None:
                account = ProviderBudgetAccount(
                    tenant_id=self.tenant_id,
                    committed_calls=0,
                    committed_input=0,
                    committed_output=0,
                    blocked=False,
                )
                session.add(account)
            require(
                calls_limit >= account.committed_calls
                and input_limit >= account.committed_input
                and output_limit >= account.committed_output,
                "O novo teto não pode apagar consumo ou reservas existentes.",
            )
            account.calls_limit, account.input_limit, account.output_limit = (
                calls_limit,
                input_limit,
                output_limit,
            )
            account.configured_reason = reason.strip()
            account.updated_at = utcnow()
            # Increasing ceilings never clears an overrun block or resets consumption.

    def summary(self) -> dict[str, Any]:
        with self.transaction() as session:
            account = self.account(session)
            rows = session.scalars(
                select(ProviderReservation)
                .where(ProviderReservation.tenant_id == self.tenant_id)
                .order_by(ProviderReservation.created_at)
            ).all()
            return {
                "tenant_id": self.tenant_id,
                "limits": {
                    "calls": account.calls_limit,
                    "input_units": account.input_limit,
                    "output_units": account.output_limit,
                },
                "committed": {
                    "calls": account.committed_calls,
                    "input_units": account.committed_input,
                    "output_units": account.committed_output,
                },
                "blocked": account.blocked,
                "blocked_reason": account.blocked_reason,
                "reservations": [
                    {
                        "call_id": row.call_id,
                        "request_id": row.request_id,
                        "state": row.state,
                        "reserved_input": row.reserved_input,
                        "reserved_output": row.reserved_output,
                        "model_requested": row.model_requested,
                        "observation": row.observation,
                        "observation_source": row.observation_source,
                        "evidence_reference": row.evidence_reference,
                    }
                    for row in rows
                ],
                "contract": "Cumulative operational allowance. Known reported tokens replace reservations; unknown calls remain reserved. No prices, invoice guarantee or automatic expiry.",
            }
