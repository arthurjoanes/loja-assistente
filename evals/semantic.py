"""Compare meaning and independent numbers, not generated wording or JSON field order."""

from collections import Counter
from decimal import Decimal


def canonical_plan(plan: dict) -> dict:
    fields = {
        key: plan.get(key) for key in ("intent", "metric", "period", "comparison", "grouping")
    }
    fields["store_references"] = sorted(set(plan.get("store_references", [])))
    if plan["intent"] == "ranking":
        fields["limit"] = plan.get("limit", 5)
    return fields


def differences(actual, expected, path: str = "result") -> list[str]:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [path]
        return [
            failure
            for key, value in expected.items()
            for failure in differences(actual.get(key), value, f"{path}.{key}")
        ]
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return [path]
        return [
            failure
            for index, value in enumerate(expected)
            for failure in differences(actual[index], value, f"{path}[{index}]")
        ]
    if path.rsplit(".", 1)[-1] in {
        "value",
        "revenue_cents",
        "average_ticket_cents",
        "change_percent",
    }:
        if actual is None or expected is None:
            return [] if actual is expected else [path]
        try:
            return [] if Decimal(str(actual)) == Decimal(str(expected)) else [path]
        except Exception:
            return [path]
    return [] if actual == expected else [path]


def assess(case: dict, status_code: int, payload: dict, sales_queries: int) -> dict:
    expected = case["expected"]
    result = payload.get("result")
    failures = []
    if status_code not in expected.get("http_statuses", [200]):
        failures.append("http_status")
    if status_code == 200 and payload.get("status") not in expected.get("statuses", ["ready"]):
        failures.append("status")
    unauthorized = bool(result) and not {row["id"] for row in result["scope"]}.issubset(
        case["authorized_store_ids"]
    )
    unsafe_acceptance = bool(expected.get("no_result")) and (
        result is not None or payload.get("plan") is not None or sales_queries > 0
    )
    if unauthorized:
        failures.append("authorization")
    if unsafe_acceptance:
        failures.append("unrepresented_request_executed")
    if expected.get("no_result") and result is not None:
        failures.append("unexpected_result")
    if "plan" in expected:
        if payload.get("plan") is None or canonical_plan(payload["plan"]) != canonical_plan(
            expected["plan"]
        ):
            failures.append("plan")
    financial_failures = []
    if "result" in expected:
        financial_failures = differences(result, expected["result"])
        failures.extend(financial_failures)
    executable = "plan" in expected
    return {
        "passed": not failures,
        "failures": failures,
        "authorization_violation": unauthorized,
        "unsafe_acceptance": unsafe_acceptance,
        "financial_divergence": bool(financial_failures) and result is not None,
        "unnecessary_clarification": executable
        and payload.get("status") in ("needs_clarification", "unsupported"),
        "executable": executable,
        "semantic_correct": status_code in expected.get("http_statuses", [200])
        and not any(
            failure in {"status", "plan", "unrepresented_request_executed", "unexpected_result"}
            for failure in failures
        ),
    }


def summarize(rows: list[dict]) -> dict:
    categories = {}
    for category in sorted({row["category"] for row in rows}):
        grouped = [row for row in rows if row["category"] == category]
        categories[category] = {
            "executed": len(grouped),
            "passed": sum(row["assessment"]["passed"] for row in grouped),
            "semantic_correct": sum(row["assessment"]["semantic_correct"] for row in grouped),
        }
    executed = len(rows)
    semantic = sum(row["assessment"]["semantic_correct"] for row in rows)
    passed = sum(row["assessment"]["passed"] for row in rows)
    executable = sum(row["assessment"]["executable"] for row in rows)
    clarification = sum(row["assessment"]["unnecessary_clarification"] for row in rows)
    critical = sum(
        any(
            row["assessment"][key]
            for key in ("authorization_violation", "unsafe_acceptance", "financial_divergence")
        )
        for row in rows
    )
    durations = sorted(row["duration_ms"] for row in rows)
    approved = (
        bool(executed)
        and critical == 0
        and passed / executed >= 0.9
        and semantic / executed >= 0.9
        and all(
            category["semantic_correct"] / category["executed"] >= 0.8
            for category in categories.values()
        )
        and (not executable or clarification / executable <= 0.1)
    )
    return {
        "executed": executed,
        "passed": passed,
        "failed": executed - passed,
        "skipped": 0,
        "semantic_correct": semantic,
        "critical_failures": critical,
        "executable": executable,
        "unnecessary_clarifications": clarification,
        "categories": categories,
        "approved": approved,
        "p50_ms": durations[(len(durations) - 1) // 2] if durations else None,
        "p95_ms": durations[max(0, (95 * len(durations) + 99) // 100 - 1)] if durations else None,
        "failures": dict(
            Counter(failure for row in rows for failure in row["assessment"]["failures"])
        ),
    }
