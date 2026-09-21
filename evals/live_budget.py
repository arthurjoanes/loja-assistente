"""Conservative, persisted reservations shared by smoke/development/final evaluation."""

import json
import os
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit


class BudgetStopped(RuntimeError):
    pass


def exceeds_reservation(trace: dict, reservation: tuple[int, int]) -> bool:
    reserved_input, reserved_output = reservation
    return any(
        type(trace.get(field)) is int and trace[field] > limit
        for field, limit in (
            ("input_tokens", reserved_input),
            ("output_tokens", reserved_output),
            ("total_tokens", reserved_input + reserved_output),
        )
    )


class LiveBudget:
    def __init__(self, authorization: Path, endpoint: str, model: str, stage: str) -> None:
        self.authorization = authorization.resolve()
        project = Path(__file__).resolve().parents[1]
        runtime = project / ".runtime"
        if not self.authorization.is_relative_to(runtime):
            raise BudgetStopped("A autorização local deve ficar em .runtime, ignorado pelo Git.")
        self.contract = json.loads(self.authorization.read_text(encoding="utf-8-sig"))
        contract = self.contract
        self.contract_hash = sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()
        if contract.get("authorized") is not True or not contract.get("approval_id"):
            raise BudgetStopped("Falta autorização explícita para esta rodada.")
        self.deadline = datetime.fromisoformat(contract["expires_at"])
        if self.deadline.tzinfo is None:
            raise BudgetStopped("A validade da autorização deve conter fuso UTC explícito.")
        if self.deadline <= datetime.now(UTC):
            raise BudgetStopped("Autorização expirada.")
        if (
            contract["endpoint"].rstrip("/") != endpoint.rstrip("/")
            or contract["deployment"] != model
        ):
            raise BudgetStopped("Endpoint/deployment difere da autorização.")
        if stage not in contract["stages"]:
            raise BudgetStopped("Etapa fora da autorização.")
        for key in ("max_calls", "max_input_tokens", "max_output_tokens"):
            if type(contract[key]) is not int or contract[key] <= 0:
                raise BudgetStopped("Limites operacionais devem ser inteiros positivos.")
        if contract["max_calls"] > 61:
            raise BudgetStopped("Esta rodada admite no máximo 61 tentativas, incluindo falhas.")
        self.input_price = self._price("input_usd_per_million")
        self.output_price = self._price("output_usd_per_million")
        self.cost_cap = self._price("max_estimated_usd")
        if (
            self.cost_cap <= 0
            or not contract.get("price_checked_at")
            or not contract.get("price_source")
        ):
            raise BudgetStopped("Documente preço, data e teto antes da execução live.")
        if urlsplit(contract["price_source"]).scheme != "https":
            raise BudgetStopped("A fonte de preço deve ser uma URL HTTPS verificável.")
        budget_directory = runtime / "llm-budgets"
        budget_directory.mkdir(exist_ok=True)
        identifier = sha256(str(contract["approval_id"]).encode()).hexdigest()
        self.journal = budget_directory / f"{identifier}.ledger.jsonl"
        self.lock = budget_directory / f"{identifier}.lock"
        self.lock_fd: int | None = None
        self.calls = self.input_reserved = self.output_reserved = 0
        self.estimated_reserved = Decimal(0)
        self.reservations: dict[str, tuple[int, int]] = {}
        self.reservation_exceeded = False

    def _price(self, key: str) -> Decimal:
        value = Decimal(str(self.contract[key]))
        if not value.is_finite() or value < 0:
            raise BudgetStopped("Preço/teto deve ser decimal finito e não negativo.")
        return value

    def __enter__(self):
        try:
            self.lock_fd = os.open(self.lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise BudgetStopped(
                "Rodada já em execução ou lock de interrupção pendente; confira antes de retomar."
            ) from exc
        try:
            if self.journal.exists():
                for line in self.journal.read_text(encoding="utf-8").splitlines():
                    entry = json.loads(line)
                    if (
                        entry["approval_id"] != self.contract["approval_id"]
                        or entry.get("contract_sha256") != self.contract_hash
                    ):
                        raise BudgetStopped("Não reutilize ledger de outra autorização.")
                    if entry["event"] == "reserved":
                        self.calls += 1
                        self.input_reserved += entry["input_reserved"]
                        self.output_reserved += entry["output_reserved"]
                        self.estimated_reserved += Decimal(entry["estimated_reserved_usd"])
                        self.reservations[entry["call_id"]] = (
                            entry["input_reserved"],
                            entry["output_reserved"],
                        )
                    elif entry["event"] == "observed" and exceeds_reservation(
                        entry["trace"], self.reservations[entry["trace"]["call_id"]]
                    ):
                        # observed is durable before the optional marker; a crash between
                        # those writes must not restore permission to call the provider.
                        raise BudgetStopped(
                            "Uso medido excedeu uma reserva nesta rodada; confira orçamento antes de outra autorização."
                        )
                    elif entry["event"] == "reservation_exceeded":
                        raise BudgetStopped(
                            "Uso medido excedeu uma reserva nesta rodada; confira orçamento antes de outra autorização."
                        )
            return self
        except Exception:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_args):
        if self.lock_fd is not None:
            os.close(self.lock_fd)
            self.lock_fd = None
            self.lock.unlink()

    def append(self, entry: dict) -> None:
        if self.lock_fd is None:
            raise BudgetStopped("Reserva sem lock de execução.")
        entry = {
            "at": datetime.now(UTC).isoformat(),
            "approval_id": self.contract["approval_id"],
            "contract_sha256": self.contract_hash,
            **entry,
        }
        with self.journal.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def reserve(self, call_id: str, input_tokens: int, output_tokens: int) -> None:
        if self.reservation_exceeded:
            raise BudgetStopped("Uso medido excedeu a reserva; rodada interrompida.")
        if self.deadline <= datetime.now(UTC):
            raise BudgetStopped("Autorização expirou durante a rodada.")
        cost = (input_tokens * self.input_price + output_tokens * self.output_price) / 1_000_000
        if (
            self.calls + 1 > self.contract["max_calls"]
            or self.input_reserved + input_tokens > self.contract["max_input_tokens"]
            or self.output_reserved + output_tokens > self.contract["max_output_tokens"]
            or self.estimated_reserved + cost > self.cost_cap
        ):
            raise BudgetStopped(
                "Próxima chamada ultrapassaria a reserva autorizada; nenhuma chamada enviada."
            )
        self.append(
            {
                "event": "reserved",
                "call_id": call_id,
                "input_reserved": input_tokens,
                "output_reserved": output_tokens,
                "estimated_reserved_usd": str(cost),
            }
        )
        self.calls += 1
        self.input_reserved += input_tokens
        self.output_reserved += output_tokens
        self.estimated_reserved += cost
        self.reservations[call_id] = (input_tokens, output_tokens)

    def record(self, trace: dict) -> None:
        self.append({"event": "observed", "trace": trace})
        if exceeds_reservation(trace, self.reservations[trace["call_id"]]):
            self.reservation_exceeded = True
            self.append({"event": "reservation_exceeded", "call_id": trace["call_id"]})
            raise BudgetStopped(
                "Uso medido excedeu reserva conservadora; próximas chamadas interrompidas."
            )

    def summary(self) -> dict:
        return {
            "approval_id": self.contract["approval_id"],
            "calls_reserved": self.calls,
            "input_tokens_reserved": self.input_reserved,
            "output_tokens_reserved": self.output_reserved,
            "estimated_reserved_usd": str(self.estimated_reserved),
            "price_source": self.contract["price_source"],
            "price_checked_at": self.contract["price_checked_at"],
            "actual_invoice": None,
            "note": "Reserva conservadora de bytes UTF-8 + margem; não é tokenização exata nem fatura. Falhas sem uso conhecido mantêm a reserva.",
        }
