"""Local administration of cumulative operational limits, not money or an invoice.

No daily reset or release of unknown usage. Reconciliation requires complete
provider-reported usage and an evidence reference; it never queries the provider.
Use the configured database intentionally. This command has no HTTP endpoint.
"""

import argparse
import json

from loja_assistente.assistant.budget import DurableBudget
from loja_assistente.assistant.budget_policy import BudgetRejected
from loja_assistente.assistant.provider_trace import ProviderTrace


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    configure = commands.add_parser(
        "configure",
        help="Set absolute cumulative ceilings; never resets counters or clears overrun blocks",
    )
    configure.add_argument("--calls", required=True, type=int)
    configure.add_argument("--input-units", required=True, type=int)
    configure.add_argument("--output-units", required=True, type=int)
    configure.add_argument("--reason", required=True)
    commands.add_parser("status", help="Show reservations, reported usage and unknown calls")
    reconcile = commands.add_parser(
        "reconcile",
        help="Record observed complete usage; never estimate zero to release an unknown call",
    )
    reconcile.add_argument("--call-id", required=True)
    reconcile.add_argument("--input-tokens", required=True, type=int)
    reconcile.add_argument("--output-tokens", required=True, type=int)
    reconcile.add_argument("--total-tokens", required=True, type=int)
    reconcile.add_argument("--provider-request-id", required=True)
    reconcile.add_argument("--response-id")
    reconcile.add_argument("--evidence-reference", required=True)
    args = parser.parse_args()
    try:
        budget = DurableBudget(args.tenant, "local-budget-admin", "local-budget-admin")
        if args.command == "configure":
            budget.configure(args.calls, args.input_units, args.output_units, args.reason)
        elif args.command == "reconcile":
            rows = budget.summary()["reservations"]
            row = next((row for row in rows if row["call_id"] == args.call_id), None)
            if row is None:
                raise BudgetRejected("Reserva não encontrada nesta organização.")
            previous = row["observation"] or {}
            trace = ProviderTrace(
                call_id=args.call_id,
                model_requested=row["model_requested"],
                prompt_sha256=previous.get("prompt_sha256", ""),
                schema_sha256=previous.get("schema_sha256", ""),
                provider_request_id=args.provider_request_id,
                response_id=args.response_id or previous.get("response_id"),
                model_returned=previous.get("model_returned"),
                input_tokens=args.input_tokens,
                output_tokens=args.output_tokens,
                total_tokens=args.total_tokens,
                status="operator_reconciled",
            )
            budget.reconcile(
                trace, source="operator_evidence", evidence_reference=args.evidence_reference
            )
        print(json.dumps(budget.summary(), ensure_ascii=False, default=str))
        return 0
    except BudgetRejected as error:
        print(json.dumps({"status": "rejected", "message": str(error)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
