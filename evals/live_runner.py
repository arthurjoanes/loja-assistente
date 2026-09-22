"""Bounded comparison through FastAPI + isolated PostgreSQL; live is opt-in and authorized."""

import argparse
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import time
from contextlib import ExitStack, nullcontext
from dataclasses import asdict
from datetime import UTC, date, datetime
from decimal import Decimal
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from uuid import uuid4

from evals.live_budget import BudgetStopped, LiveBudget
from evals.semantic import assess, summarize

PROJECT = Path(__file__).resolve().parents[1]
CASE_DIR = PROJECT / "evals" / "cases"
FREEZE = PROJECT / "evals" / "freeze.json"


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def source_fingerprint() -> dict:
    files = []
    for directory in ("backend/src", "backend/tests", "backend/migrations", "evals"):
        files.extend((PROJECT / directory).rglob("*.py"))
    files.extend(
        PROJECT / name for name in ("backend/uv.lock", "backend/pyproject.toml", "compose.yaml")
    )
    return {
        str(path.relative_to(PROJECT)).replace("\\", "/"): digest(path) for path in sorted(files)
    }


def freeze() -> None:
    final_path = CASE_DIR / "final-v1.json"
    if not final_path.exists():
        raise SystemExit("Revisor precisa preparar final-v1.json antes do freeze.")
    if FREEZE.exists():
        raise SystemExit(
            "Freeze existente: preserve a rodada; não sobrescreva para esconder ajustes."
        )
    # Hash only. The implementer does not need to inspect the held-out examples.
    content = {
        "at": datetime.now(UTC).isoformat(),
        "source": source_fingerprint(),
        "development_sha256": digest(CASE_DIR / "development-v1.json"),
        "final_sha256": digest(final_path),
        "blindness": "independent reviewer; implementer opens final only after this freeze",
    }
    FREEZE.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")
    print("Código e casos congelados em evals/freeze.json; nenhuma chamada enviada.")


def verify_freeze() -> dict:
    frozen = json.loads(FREEZE.read_text(encoding="utf-8"))
    if (
        frozen["source"] != source_fingerprint()
        or frozen["final_sha256"] != digest(CASE_DIR / "final-v1.json")
        or frozen["development_sha256"] != digest(CASE_DIR / "development-v1.json")
    ):
        raise RuntimeError(
            "Código ou holdout mudou após freeze. Preserve resultados e declare uma nova revisão."
        )
    return frozen


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def aggregate_usage(traces: list[dict]) -> dict:
    fields = ("input_tokens", "output_tokens", "total_tokens")

    def valid(value):
        return type(value) is int and value >= 0

    totals = {
        name: sum(trace[name] for trace in traces if valid(trace.get(name))) for name in fields
    }
    totals["unknown_usage_calls"] = sum(
        not all(valid(trace.get(name)) for name in fields)
        or trace["input_tokens"] + trace["output_tokens"] != trace["total_tokens"]
        for trace in traces
    )
    return totals


def evaluation_status(
    mode: str,
    stage: str,
    summaries: dict,
    model_calls: int,
    unchanged: bool,
    stopped: bool,
    frozen: bool,
) -> tuple[str, bool]:
    structured_ok = summaries["structured"]["failed"] == 0
    if mode == "offline":
        return "offline_only", structured_ok and unchanged and not stopped
    quality = (
        structured_ok
        and summaries["llm"]["approved"]
        and model_calls > 0
        and unchanged
        and not stopped
    )
    if stage == "final":
        categories = summaries["llm"]["categories"]
        complete = (
            summaries["llm"]["executed"] == 48
            and len(categories) == 6
            and all(category["executed"] == 8 for category in categories.values())
        )
        approved = quality and frozen and complete
        return "live_final_approved" if approved else "live_final_not_approved", approved
    expected = 1 if stage == "smoke" else 12
    passed = quality and summaries["llm"]["executed"] == expected
    return f"live_{stage}_{'passed' if passed else 'not_passed'}", passed


def known_usage_cost(usage: dict, budget: LiveBudget) -> str:
    return str(
        (
            Decimal(usage["input_tokens"]) * budget.input_price
            + Decimal(usage["output_tokens"]) * budget.output_price
        )
        / 1_000_000
    )


def run(mode: str, stage: str, authorization: Path | None) -> int:
    sys.path.insert(0, str(PROJECT / "backend" / "tests"))
    from sqlalchemy.engine import make_url

    url = os.environ.get("TEST_DATABASE_URL", "")
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql" or not (parsed.database or "").endswith("_test"):
        raise RuntimeError("Defina TEST_DATABASE_URL para PostgreSQL descartável com sufixo _test.")
    os.environ["DATABASE_URL"] = url
    os.environ["DEMO_MODE"] = "true"
    from fastapi.testclient import TestClient
    from manual_fixture import IDENTITIES, ORIGIN, PASSWORD, seed_manual
    from sqlalchemy import event, text
    from sqlalchemy.orm import Session

    from evals.database import prepare_test_database
    from loja_assistente.app import app
    from loja_assistente.assistant.interpreters import demo, openai_adapter
    from loja_assistente.assistant.provider_trace import EvaluationHooks, observe_provider
    from loja_assistente.config import settings
    from loja_assistente.database import get_db

    frozen = verify_freeze() if stage == "final" else None
    path = CASE_DIR / ("final-v1.json" if stage == "final" else "development-v1.json")
    suite = json.loads(path.read_text(encoding="utf-8"))
    expected_count = 24 if stage == "final" else 12
    if (
        len(suite["cases"]) != expected_count
        or len({c["id"] for c in suite["cases"]}) != expected_count
    ):
        raise RuntimeError("Amostra diverge do contrato de avaliação prévio.")
    cases = suite["cases"][:1] if stage == "smoke" else suite["cases"]
    repeats = 2 if stage == "final" else 1
    if mode == "live":
        if authorization is None or not settings.openai_api_key:
            raise BudgetStopped(
                "Configure chave local e forneça autorização delimitada antes de chamar o provedor."
            )
        budget_context = LiveBudget(
            authorization, settings.openai_base_url, settings.openai_model, stage
        )
    else:
        budget_context = nullcontext(None)
    settings.llm_enabled = mode == "live"
    settings.reference_date = date(2026, 8, 17)
    settings.dataset_version = "manual-v1"
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("loja_assistente.operations").setLevel(logging.WARNING)
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    output = PROJECT / "evals" / "reports" / run_id
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    modes = ["demo", "structured"] + (["llm"] if mode == "live" else [])
    outcomes = []
    all_traces = []
    stop_reason = None
    environment = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "transport": "FastAPI TestClient / ASGI + real PostgreSQL",
        "openai_adapter": openai_adapter.VERSION,
        "demo": demo.VERSION,
        "openai_sdk": version("openai"),
    }
    metadata = {
        "run_id": run_id,
        "started_at": datetime.now(UTC).isoformat(),
        "mode": mode,
        "stage": stage,
        "case_sha256": digest(path),
        "source": source_fingerprint(),
        "fixture": "manual-v1",
        "seed": 0,
        "repetitions": repeats,
        "frozen": frozen,
        "deployment": settings.openai_model if mode == "live" else None,
        "inference_endpoint": settings.openai_base_url if mode == "live" else None,
        "inference_reasoning_effort": settings.openai_reasoning_effort if mode == "live" else None,
        "max_output_tokens": openai_adapter.MAX_OUTPUT_TOKENS,
        "inference_timeout_seconds": 12.0,
        "inference_max_retries": 0,
        "command": [arg for arg in sys.argv],
        "environment": environment,
    }
    revision = (
        subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"], cwd=PROJECT, capture_output=True, text=True
        )
        if shutil.which("git")
        else None
    )
    metadata["git_revision"] = (
        revision.stdout.strip() if revision and revision.returncode == 0 else None
    )
    metadata["revision_note"] = (
        "Exact file fingerprints identify this run; a Git revision is not fabricated when unavailable in the evaluation image."
    )
    write_json(output / "manifest.json", metadata)
    engine = None
    budget = None
    budget_summary = None
    infrastructure_failure = None
    operation_phase = "prepare_test_database"
    try:
        engine = prepare_test_database(url)
        with ExitStack() as resources:
            operation_phase = "budget_lock"
            budget = resources.enter_context(budget_context)
            operation_phase = "database_connect"
            connection = resources.enter_context(engine.connect())
            operation_phase = "stage_journal"
            if budget:
                previous = (
                    budget.journal.read_text(encoding="utf-8") if budget.journal.exists() else ""
                )
                if any(
                    json.loads(line).get("stage") == stage
                    and json.loads(line)["event"] == "stage_started"
                    for line in previous.splitlines()
                ):
                    raise BudgetStopped(
                        "Etapa já tentada nesta autorização; preserve a tentativa e solicite nova rodada."
                    )
                budget.append({"event": "stage_started", "stage": stage, "run_id": run_id})
            operation_phase = "database_transaction"
            if budget:
                from evals.api_budget import prepare_api_budget

                operation_phase = "application_budget_setup"
                metadata["application_budget"] = prepare_api_budget(engine, budget)
                operation_phase = "database_transaction"
            outer = connection.begin()
            resources.callback(outer.rollback)
            session = Session(bind=connection, join_transaction_mode="create_savepoint")
            resources.callback(session.close)
            environment["postgresql"] = connection.scalar(text("SHOW server_version"))
            operation_phase = "seed_manual"
            seed_manual(session, organizations_preseeded=budget is not None)
            session.commit()

            def override_database():
                yield session

            app.dependency_overrides[get_db] = override_database
            operation_phase = "execute_cases"
            try:
                for repetition in range(1, repeats + 1):
                    for case in cases:
                        for interpreter in modes:
                            if interpreter == "structured" and "plan" not in case["expected"]:
                                continue
                            row = {
                                "id": case["id"],
                                "category": case["category"],
                                "identity": case["identity"],
                                "mode": interpreter,
                                "repetition": repetition,
                                "question": case["question"],
                                "expected": case["expected"],
                                "provider": [],
                            }
                            clock = time.perf_counter()
                            statements = []

                            def count_sales(
                                _conn, _cursor, statement, _params, _ctx, _many, recorded=statements
                            ):
                                sql = statement.casefold()
                                if "from orders" in sql or "join order_items" in sql:
                                    recorded.append(True)

                            def record_provider(trace, target=row):
                                record = asdict(trace)
                                target["provider"].append(record)
                                all_traces.append(record)
                                if budget:
                                    budget.record(record)

                            try:
                                if stop_reason or time.monotonic() - started > 900:
                                    raise BudgetStopped(
                                        stop_reason
                                        or "Tempo operacional da rodada excedeu 900 segundos."
                                    )
                                with TestClient(
                                    app, base_url=ORIGIN, headers={"Origin": ORIGIN}
                                ) as client:
                                    login = client.post(
                                        "/api/auth/login",
                                        json={
                                            "email": IDENTITIES[case["identity"]],
                                            "password": PASSWORD,
                                        },
                                    )
                                    if login.status_code != 200:
                                        raise RuntimeError("Falha de autenticação da fixture.")
                                    client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
                                    body = {
                                        "question": case["question"],
                                        "mode": interpreter,
                                        "store_ids": case.get("store_ids", []),
                                        "period": case.get("period"),
                                    }
                                    if "prior_question" in case and interpreter != "structured":
                                        prior = client.post(
                                            "/api/assistant/query",
                                            json={
                                                "question": case["prior_question"],
                                                "mode": "demo",
                                            },
                                        )
                                        if (
                                            prior.status_code != 200
                                            or prior.json()["status"] != "ready"
                                        ):
                                            raise RuntimeError(
                                                "Setup de continuação falhou; não é falha do modelo."
                                            )
                                        body["conversation_id"] = prior.json()["conversation_id"]
                                    event.listen(connection, "before_cursor_execute", count_sales)
                                    try:
                                        hooks = (
                                            observe_provider(
                                                EvaluationHooks(budget.reserve, record_provider)
                                            )
                                            if interpreter == "llm"
                                            else nullcontext()
                                        )
                                        with hooks:
                                            response = (
                                                client.post(
                                                    "/api/analytics/query",
                                                    json=case["expected"]["plan"],
                                                )
                                                if interpreter == "structured"
                                                else client.post("/api/assistant/query", json=body)
                                            )
                                    finally:
                                        event.remove(
                                            connection, "before_cursor_execute", count_sales
                                        )
                                    payload = response.json()
                                    if interpreter == "structured" and response.status_code == 200:
                                        payload = {
                                            "status": "no_data"
                                            if payload["coverage"]["status"] == "absent"
                                            else "ready",
                                            "plan": case["expected"]["plan"],
                                            "result": payload,
                                        }
                                    row["http_status"] = response.status_code
                                    row["observed"] = payload
                                    row["sales_queries"] = len(statements)
                                    row["assessment"] = assess(
                                        case, response.status_code, payload, len(statements)
                                    )
                                    # Persistence/evidence must equal the same analytical object.
                                    if interpreter != "structured" and payload.get("result"):
                                        evidence = client.get(
                                            f"/api/answers/{payload['id']}/evidence"
                                        )
                                        if (
                                            evidence.status_code != 200
                                            or evidence.json() != payload["result"]
                                        ):
                                            row["assessment"]["passed"] = False
                                            row["assessment"]["financial_divergence"] = True
                                            row["assessment"]["failures"].append(
                                                "persisted_evidence"
                                            )
                            except Exception as exc:
                                if isinstance(exc, BudgetStopped):
                                    stop_reason = str(exc)
                                row["error_type"] = type(exc).__name__
                                # Do not copy exception text: SDK/connection strings may carry secrets.
                                row["assessment"] = {
                                    "passed": False,
                                    "semantic_correct": False,
                                    "failures": ["infrastructure_or_budget"],
                                    "authorization_violation": False,
                                    "unsafe_acceptance": False,
                                    "financial_divergence": False,
                                    "unnecessary_clarification": False,
                                    "executable": "plan" in case["expected"],
                                }
                                session.rollback()
                            row["duration_ms"] = round((time.perf_counter() - clock) * 1000)
                            outcomes.append(row)
                            with (output / "cases.jsonl").open("a", encoding="utf-8") as handle:
                                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                            print(
                                f"{case['id']} {interpreter} repetition={repetition} passed={row['assessment']['passed']}",
                                flush=True,
                            )
            finally:
                app.dependency_overrides.clear()
            operation_phase = "cleanup"
    except Exception as exc:
        # Setup failures must leave evidence without copying connection strings or SDK text.
        infrastructure_failure = {"phase": operation_phase, "error_type": type(exc).__name__}
        stop_reason = "Falha de infraestrutura da rodada; consulte infrastructure_failure."
    finally:
        if budget:
            budget_summary = budget.summary()
        if engine is not None:
            try:
                engine.dispose()
            except Exception as exc:
                if infrastructure_failure is None:
                    infrastructure_failure = {
                        "phase": "engine_dispose",
                        "error_type": type(exc).__name__,
                    }
                    stop_reason = (
                        "Falha de infraestrutura da rodada; consulte infrastructure_failure."
                    )
    summaries = {
        name: summarize([row for row in outcomes if row["mode"] == name]) for name in modes
    }
    for name in modes:
        group = [row for row in outcomes if row["mode"] == name]
        summaries[name]["provider_invoked_cases"] = sum(bool(row["provider"]) for row in group)
        summaries[name]["local_guard_cases"] = sum(
            name == "llm" and not row["provider"] and "error_type" not in row for row in group
        )
    usage = aggregate_usage(all_traces)
    report = {
        **metadata,
        "finished_at": datetime.now(UTC).isoformat(),
        "summaries": summaries,
        "measured_usage": usage,
        "budget": budget_summary,
        "stop_reason": stop_reason,
        "infrastructure_failure": infrastructure_failure,
        "live_model_calls": len(all_traces),
        "not_applicable_structured_cases_per_repeat": len(cases)
        - sum("plan" in c["expected"] for c in cases),
        "utility_with_users": "not_evaluated",
        "production": "not_evaluated",
    }
    if budget_summary and budget:
        report["estimated_known_usage_usd"] = known_usage_cost(usage, budget)
        report["cost_estimate_completeness"] = (
            "partial" if usage["unknown_usage_calls"] else "complete_measured_calls"
        )
        report["invoice_verified"] = False
    report["source_and_cases_unchanged"] = (
        source_fingerprint() == metadata["source"] and digest(path) == metadata["case_sha256"]
    )
    report["status"], passed = evaluation_status(
        mode,
        stage,
        summaries,
        len(all_traces),
        report["source_and_cases_unchanged"],
        bool(stop_reason),
        bool(frozen),
    )
    report["exit_code"] = 0 if passed else 1
    write_json(output / "summary.json", report)
    write_json(output / "manifest.json", metadata)
    lines = [
        f"# Avaliação {run_id}",
        "",
        f"Estado: **{report['status']}**. Etapa: {stage}. Fixture manual-v1; PostgreSQL {environment.get('postgresql', 'indisponível')}.",
        "",
        "| Modo | Casos | Passaram | Falharam | Semântica | p95 ms |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, summary in summaries.items():
        lines.append(
            f"| {name} | {summary['executed']} | {summary['passed']} | {summary['failed']} | {summary['semantic_correct']} | {summary['p95_ms']} |"
        )
    lines += [
        "",
        "Esperado/observado e falhas: cases.jsonl. Schema e fonte: manifest.json. Uso medido e reserva: summary.json.",
        "Latência inclui autenticação sintética e transporte ASGI; não mede navegador, rede do cliente ou produção.",
        "Casos não executados após interrupção permanecem como falha no denominador. Consulta estruturada não se aplica às recusas.",
        "A amostra técnica não mede produtividade de usuários. Transporte simulado não integra esta rodada live.",
    ]
    (output / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Relatório: {output}; {report['status']}")
    return report["exit_code"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--mode", choices=["offline", "live"], default="offline")
    parser.add_argument("--stage", choices=["smoke", "development", "final"], default="development")
    parser.add_argument("--authorization", type=Path)
    args = parser.parse_args()
    if args.freeze:
        freeze()
        return
    raise SystemExit(run(args.mode, args.stage, args.authorization))


if __name__ == "__main__":
    main()
