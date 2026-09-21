"Executa avaliações com FastAPI e PostgreSQL."

import argparse
import json
import logging
import os
import platform
import sys
import time
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path


def run(output_directory: Path) -> int:
    project = Path(__file__).resolve().parents[1]
    if not output_directory.resolve().is_relative_to(project):
        raise RuntimeError("O relatório deve ficar dentro da pasta deste projeto.")
    sys.path.insert(0, str(project))
    sys.path.insert(0, str(project / "backend" / "src"))
    sys.path.insert(0, str(project / "backend" / "tests"))

    from fastapi.testclient import TestClient
    from manual_fixture import IDENTITIES, ORIGIN, PASSWORD, seed_manual
    from sqlalchemy import text
    from sqlalchemy.orm import Session

    from evals.database import prepare_test_database
    from evals.harness import EvaluationFailure, check_http, execute_case, load_suite
    from loja_assistente.app import app
    from loja_assistente.config import settings
    from loja_assistente.database import get_db

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("loja_assistente.operations").setLevel(logging.WARNING)

    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url:
        raise RuntimeError("Defina TEST_DATABASE_URL: avaliações exigem PostgreSQL dedicado.")
    settings.dataset_version = "manual-v1"
    settings.reference_date = date(2026, 8, 17)
    suite = load_suite()
    engine = prepare_test_database(url)
    outcomes = []
    try:
        with engine.connect() as connection:
            outer = connection.begin()
            session = Session(bind=connection, join_transaction_mode="create_savepoint")
            database_version = connection.scalar(text("SELECT version()"))
            seed_manual(session)
            session.commit()

            def override_database():
                yield session

            app.dependency_overrides[get_db] = override_database
            try:
                for case in suite["cases"]:
                    started = time.perf_counter()
                    outcome = {
                        "id": case["id"],
                        "category": case["category"],
                        "mode": case["mode"],
                        "identity": case["identity"],
                        "status": "passed",
                    }
                    try:
                        with TestClient(app, base_url=ORIGIN, headers={"Origin": ORIGIN}) as client:
                            response = client.post(
                                "/api/auth/login",
                                json={
                                    "email": IDENTITIES[case["identity"]],
                                    "password": PASSWORD,
                                },
                            )
                            check_http(response, 200)
                            client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
                            outcome["observed"] = execute_case(client, case)
                    except Exception as exc:
                        outcome["status"] = "failed"
                        outcome["failure_stage"] = (
                            exc.stage
                            if isinstance(exc, EvaluationFailure)
                            else "infrastructure/unknown"
                        )
                        outcome["error"] = f"{type(exc).__name__}: {exc}"
                        session.rollback()
                    outcome["duration_ms"] = round((time.perf_counter() - started) * 1000)
                    outcomes.append(outcome)
            finally:
                app.dependency_overrides.clear()
                session.close()
                outer.rollback()
    finally:
        engine.dispose()
    counts = Counter(item["status"] for item in outcomes)
    categories = {}
    for category in sorted({item["category"] for item in outcomes}):
        grouped = [item for item in outcomes if item["category"] == category]
        categories[category] = {
            "executed": len(grouped),
            "passed": sum(item["status"] == "passed" for item in grouped),
            "failed": sum(item["status"] == "failed" for item in grouped),
            "skipped": 0,
        }
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "cases_version": suite["version"],
        "seed": suite["seed"],
        "dataset_version": "manual-v1",
        "modes": sorted({case["mode"] for case in suite["cases"]}),
        "live_llm_evaluated": False,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "database": database_version,
            "transport": "FastAPI TestClient / HTTP ASGI",
        },
        "executed": len(outcomes),
        "passed": counts["passed"],
        "failed": counts["failed"],
        "skipped": 0,
        "categories": categories,
        "failure_stages": dict(
            Counter(item["failure_stage"] for item in outcomes if item["status"] == "failed")
        ),
        "classification_note": "category agrupa o caso; failure_stage indica a checagem que falhou. Exceções sem classificação usam infrastructure/unknown.",
        "results": outcomes,
    }
    output_directory.mkdir(parents=True, exist_ok=True)
    (output_directory / "latest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Relatório de avaliações",
        "",
        f"Executado em {report['generated_at']}; casos {suite['version']}; fixture manual-v1; seed 0.",
        "",
        f"**{len(outcomes)} executados; {counts['passed']} aprovados; "
        f"{counts['failed']} falhos; 0 ignorados.**",
        "",
        "Modos: parser demo, consulta estruturada e interpretador simulado. PostgreSQL; HTTP via TestClient.",
        "failure_stage indica a checagem que falhou. Exceções sem classificação usam infrastructure/unknown.",
        "",
        "| Categoria | Executados | Aprovados | Falhos |",
        "|---|---:|---:|---:|",
    ]
    for category, count in categories.items():
        lines.append(
            f"| {category} | {count['executed']} | {count['passed']} | {count['failed']} |"
        )
    lines.extend(["", "| Caso | Modo | Resultado |", "|---|---|---|"])
    for outcome in outcomes:
        lines.append(f"| {outcome['id']} | {outcome['mode']} | {outcome['status']} |")
    for outcome in outcomes:
        if outcome["status"] == "failed":
            lines.extend(
                [
                    "",
                    f"## Falha: {outcome['id']}",
                    "",
                    f"Checagem: {outcome['failure_stage']} · categoria nominal: {outcome['category']}",
                    "",
                    str(outcome["error"]),
                ]
            )
    (output_directory / "latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"Avaliações: {counts['passed']}/{len(outcomes)} aprovadas; relatórios em {output_directory}"
    )
    return 1 if counts["failed"] else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "reports",
    )
    args = parser.parse_args()
    raise SystemExit(run(args.output_dir))


if __name__ == "__main__":
    main()
