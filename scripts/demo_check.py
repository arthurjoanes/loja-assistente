"""Execute the documented demonstration against the running HTTP service."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import httpx

base = os.environ.get("DEMO_BASE_URL", "http://frontend:3102")
origin = os.environ.get("DEMO_ORIGIN", "http://localhost:3102")
report: list[dict[str, object]] = []


def login(client: httpx.Client, email: str) -> None:
    response = client.post("/api/auth/login", json={"email": email, "password": "LojaDemo!2026"})
    response.raise_for_status()
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]


def ask(client: httpx.Client, question: str, conversation_id: str | None = None) -> dict:
    response = client.post(
        "/api/assistant/query",
        json={"question": question, "mode": "demo", "conversation_id": conversation_id},
    )
    response.raise_for_status()
    answer = response.json()
    result = answer["result"]
    report.append(
        {
            "question": question,
            "status": answer["status"],
            "request_id": answer["request_id"],
            "scope": result["scope"] if result else None,
            "value": result["value"] if result else None,
            "period": result["period"] if result else None,
        }
    )
    return answer


with httpx.Client(base_url=base, headers={"Origin": origin}, timeout=20) as manager:
    manager.get("/").raise_for_status()
    login(manager, "gerente.a@demo.local")
    first = ask(manager, "Quanto vendi ontem?")
    assert first["status"] == "ready"
    evidence = manager.get(f"/api/answers/{first['id']}/evidence")
    evidence.raise_for_status()
    assert sum(int(row["revenue_cents"]) for row in evidence.json()["evidence"]) == int(
        first["result"]["totals"]["revenue_cents"]
    )
    ranking = ask(
        manager,
        "Quais os 5 produtos com maior receita nos últimos 7 dias?",
        first["conversation_id"],
    )
    assert len(ranking["result"]["rows"]) == 5
    comparison = ask(
        manager,
        "Compare a receita dos últimos 7 dias com o período anterior",
        first["conversation_id"],
    )
    assert comparison["result"]["comparison"] is not None
    continuation = ask(manager, "E nos sete dias anteriores?", first["conversation_id"])
    assert continuation["result"]["period"] == {"start": "2026-08-03", "end": "2026-08-10"}
    denied = manager.post(
        "/api/assistant/query", json={"question": "Receita ontem", "store_ids": ["b001"]}
    )
    assert denied.status_code == 403 and "revenue_cents" not in denied.text
    report.append({"scenario": "direct_forbidden_store", "http_status": denied.status_code})
    assert ask(manager, "Qual foi o lucro ontem?")["status"] == "unsupported"
    assert ask(manager, "Receita em 2025-01-01")["status"] == "no_data"
    manager.post("/api/auth/logout").raise_for_status()
    assert manager.get("/api/auth/me").status_code == 401
    report.append({"scenario": "logout_invalidates_session", "http_status": 401})

with httpx.Client(base_url=base, headers={"Origin": origin}, timeout=20) as other:
    login(other, "gerente.b@demo.local")
    second = ask(other, "Quanto vendi ontem?")
    assert second["result"]["scope"][0]["id"] == "b001"
    assert second["result"]["value"] != first["result"]["value"]
    denied = other.get(f"/api/answers/{first['id']}/evidence")
    assert denied.status_code == 404 and first["request_id"] not in denied.text
    report.append({"scenario": "cross_user_evidence", "http_status": denied.status_code})

destination = Path(os.environ.get("DEMO_REPORT", "/app/docs/demo-results.json"))
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(
    json.dumps(
        {
            "mode": "demo",
            "base_url": base,
            "verified_at": datetime.now(UTC).isoformat(),
            "checks": report,
        },
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
print(json.dumps(report, ensure_ascii=False, indent=2))
