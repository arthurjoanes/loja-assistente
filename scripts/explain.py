"""Inspeciona a consulta real emitida por analytics, somente na base demo."""

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from sqlalchemy import event, select, text
from sqlalchemy.engine import Connection, ExecutionContext

from loja_assistente.analytics.contracts import Period, QueryPlan
from loja_assistente.analytics.service import execute_query
from loja_assistente.auth.service import Principal
from loja_assistente.config import settings
from loja_assistente.database import SessionLocal, engine
from loja_assistente.models import Dataset, User


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("/app/docs"))
    arguments = parser.parse_args()
    if not settings.demo_mode:
        raise RuntimeError("Inspeção reservada a DEMO_MODE=true.")
    captured: list[tuple[str, dict[str, object]]] = []

    def capture(
        _connection: Connection,
        _cursor: object,
        statement: str,
        parameters: Mapping[str, object],
        _context: ExecutionContext,
        _executemany: bool,
    ) -> None:
        if statement.lstrip().startswith("SELECT sum(order_items."):
            captured.append((statement, dict(parameters)))

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "gerente.a@demo.local"))
        dataset = db.scalar(select(Dataset))
        if user is None or dataset is None:
            raise RuntimeError("Execute a migração e o seed da demonstração primeiro.")
        plan = QueryPlan(
            intent="daily",
            metric="revenue",
            grouping="day",
            store_references=["a001"],
            period=Period(start="2026-08-10", end="2026-08-17"),
        )
        event.listen(engine, "before_cursor_execute", capture)
        try:
            result = execute_query(
                db,
                Principal(user.id, user.tenant_id, user.name, user.email, user.role),
                plan,
                "local-query-plan-inspection",
            )
        finally:
            event.remove(engine, "before_cursor_execute", capture)
        if len(captured) != 1:
            raise RuntimeError(f"Esperada uma consulta diária; recebidas {len(captured)}.")
        statement, parameters = captured[0]
        # Only the statement emitted by the closed SQLAlchemy query above is inspected.
        explained = (
            db.connection()
            .exec_driver_sql("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + statement, parameters)
            .scalar_one()[0]
        )
        report = {
            "source": "Consulta SQLAlchemy real de analytics.service.execute_query",
            "database_version": db.scalar(text("SELECT version()")),
            "dataset_version": dataset.version,
            "dataset_counts": dataset.manifest["counts"],
            "scope": [store.model_dump() for store in result.scope],
            "period": result.period.model_dump(mode="json"),
            "request_id": result.request_id,
            "sql": statement,
            "parameters": parameters,
            "explain": explained,
        }
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    (arguments.output_dir / "query-plan.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8"
    )
    nodes: list[str] = []

    def inspect(node: dict[str, Any]) -> None:
        item = node["Node Type"]
        if "Index Name" in node:
            item += " · " + node["Index Name"]
        if "Relation Name" in node:
            item += " · " + node["Relation Name"]
        nodes.append(item)
        for child in node.get("Plans", []):
            inspect(child)

    inspect(explained["Plan"])
    content = (
        f"""# Plano da consulta diária

Consulta do gerente A, loja Centro (`a001`), de 10/08/2026 incluído a 17/08/2026 exclusivo. Dataset `{report["dataset_version"]}`: {report["dataset_counts"]["orders"]:,} pedidos, {report["dataset_counts"]["items"]:,} itens e seis lojas.

`EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)`: planejamento {explained["Planning Time"]} ms; execução {explained["Execution Time"]} ms.

Nós:

"""
        + "\n".join("- " + node for node in nodes)
        + "\n\n`ix_orders_scope_time` filtra tenant, loja e período; `ix_order_items_order` relaciona itens a pedidos. O PostgreSQL pode preferir varredura sequencial em tabelas pequenas ou quando lê boa parte delas. A consulta exclui dias sem cobertura.\n\n[Plano, parâmetros e SQL](query-plan.json). Para repetir após setup e seed: `docker compose run --rm backend python /app/scripts/explain.py`. O resultado fica no container; use bind de `docs` para salvá-lo no host. Exige modo demo.\n"
    )
    (arguments.output_dir / "query-plan.md").write_text(content, encoding="utf-8")
    print(
        json.dumps(
            {
                "planning_ms": explained["Planning Time"],
                "execution_ms": explained["Execution Time"],
                "nodes": nodes,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
