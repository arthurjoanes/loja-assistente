"""Mesmo avaliador estruturado usado no pytest e no relatório local."""

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal
from unittest.mock import patch

from fastapi.testclient import TestClient
from httpx import Response

CASE_FILE = Path(__file__).parent / "cases" / "manual-v1.json"
FailureStage = Literal[
    "interpretation",
    "authorization",
    "query",
    "calculation",
    "presentation",
    "infrastructure/unknown",
]


class EvaluationFailure(AssertionError):
    "Identifica a checagem que falhou."

    def __init__(self, stage: FailureStage, message: str) -> None:
        super().__init__(message)
        self.stage = stage


def require(condition: bool, stage: FailureStage, message: str) -> None:
    if not condition:
        raise EvaluationFailure(stage, message)


def load_suite() -> dict[str, Any]:
    return json.loads(CASE_FILE.read_text(encoding="utf-8"))


def check_http(response: Response, expected_status: int) -> None:
    if response.status_code == expected_status:
        return
    actual = response.status_code
    if actual in (401, 403):
        stage: FailureStage = "authorization"
    elif actual == 500:
        stage = "query"
    elif actual >= 500:
        stage = "infrastructure/unknown"
    elif actual == 422:
        stage = "interpretation"
    elif expected_status in (401, 403):
        stage = "authorization"
    elif expected_status == 422:
        stage = "interpretation"
    else:
        stage = "infrastructure/unknown"
    raise EvaluationFailure(
        stage,
        f"HTTP esperado {expected_status}, recebido {actual}: {response.text}",
    )


def assert_subset(actual: Any, expected: Any, path: str, stage: FailureStage) -> None:
    if isinstance(expected, dict):
        require(isinstance(actual, dict), stage, f"{path}: objeto esperado, recebido {actual!r}")
        for key, value in expected.items():
            child_stage = stage
            # Plano mede interpretação; campos do resultado medem sua própria checagem.
            if not path.startswith("plan"):
                if key in ("period", "coverage", "key"):
                    child_stage = "query"
                elif key in (
                    "value",
                    "revenue_cents",
                    "orders",
                    "units",
                    "average_ticket_cents",
                    "change_percent",
                ):
                    child_stage = "calculation"
                elif key in ("label", "message"):
                    child_stage = "presentation"
            require(key in actual, child_stage, f"{path}.{key}: campo ausente")
            assert_subset(actual[key], value, f"{path}.{key}", child_stage)
    elif isinstance(expected, list):
        require(
            isinstance(actual, list) and len(actual) == len(expected),
            stage,
            f"{path}: tamanho esperado {len(expected)}, recebido {actual!r}",
        )
        for index, value in enumerate(expected):
            assert_subset(actual[index], value, f"{path}[{index}]", stage)
    elif expected is not None and path.rsplit(".", 1)[-1] in {
        "value",
        "average_ticket_cents",
        "change_percent",
    }:
        try:
            equal = Decimal(str(actual)) == Decimal(str(expected))
        except InvalidOperation as exc:
            raise EvaluationFailure(stage, f"{path}: valor numérico inválido {actual!r}") from exc
        require(equal, stage, f"{path}: esperado {expected!r}, recebido {actual!r}")
    else:
        require(actual == expected, stage, f"{path}: esperado {expected!r}, recebido {actual!r}")


def execute_case(client: TestClient, case: dict[str, Any]) -> dict[str, Any]:
    expected = case["expected"]
    if case["mode"] == "interpreter_stub":
        from loja_assistente.analytics.contracts import QueryPlan
        from loja_assistente.assistant.contracts import Interpretation

        interpreted = Interpretation(
            status="ready",
            plan=QueryPlan.model_validate(case["interpreter_plan"]),
            message="",
        )
        with patch("loja_assistente.assistant.service.demo.interpret", return_value=interpreted):
            response = client.post(
                "/api/assistant/query",
                json={
                    "question": case["question"],
                    "mode": "demo",
                    "store_ids": [],
                },
            )
    elif case["mode"] == "structured":
        response = client.post("/api/analytics/query", json=case["plan"])
    else:
        conversation_id = None
        if prior_question := case.get("prior_question"):
            prior = client.post(
                "/api/assistant/query",
                json={
                    "question": prior_question,
                    "mode": "demo",
                    "store_ids": [],
                },
            )
            check_http(prior, 200)
            require(prior.json()["status"] == "ready", "interpretation", prior.text)
            conversation_id = prior.json()["conversation_id"]
        response = client.post(
            "/api/assistant/query",
            json={
                "question": case["question"],
                "mode": "demo",
                "store_ids": [],
                "conversation_id": conversation_id,
            },
        )
    check_http(response, expected["http_status"])
    payload = response.json()
    if response.status_code >= 400:
        require(
            "result" not in payload and "totals" not in payload,
            "authorization",
            "Resposta recusada expôs resultado financeiro.",
        )
        require(
            "3300" not in response.text and "Brisa Comércio" not in response.text,
            "authorization",
            "Resposta recusada expôs dados proibidos da fixture.",
        )
        return {"http_status": response.status_code}
    result = payload if case["mode"] == "structured" else payload.get("result")
    if "status" in expected:
        require(
            payload.get("status") == expected["status"],
            "interpretation",
            f"Estado esperado {expected['status']}, recebido {payload.get('status')}",
        )
    for fragment in expected.get("message_contains", []):
        require(
            fragment in payload.get("message", ""),
            "presentation",
            f"Mensagem não contém {fragment!r}: {payload.get('message')!r}",
        )
    if expected.get("no_result"):
        require(result is None, "interpretation", "Um estado sem execução retornou resultado.")
    if "plan" in expected:
        assert_subset(payload.get("plan"), expected["plan"], "plan", "interpretation")
    for key in ("value", "totals", "rows", "comparison"):
        if key in expected:
            stage: FailureStage = "query" if key in ("rows", "comparison") else "calculation"
            require(result is not None, "query", "Resultado ausente.")
            require(key in result, stage, f"Campo {key} ausente do resultado.")
            assert_subset(result[key], expected[key], key, stage)
    if "scope_ids" in expected:
        require(result is not None, "query", "Resultado ausente.")
        actual_ids = sorted(row["id"] for row in result["scope"])
        require(
            actual_ids == sorted(expected["scope_ids"]),
            "authorization",
            f"Escopo esperado {expected['scope_ids']}, recebido {actual_ids}",
        )
    if "coverage" in expected:
        require(result is not None, "query", "Resultado ausente.")
        require(
            result["coverage"]["status"] == expected["coverage"],
            "query",
            f"Cobertura esperada {expected['coverage']}, recebida {result['coverage']}",
        )
    if result is not None:
        actual_scope = {store["id"] for store in result["scope"]}
        require(
            bool(actual_scope) and actual_scope.issubset(case["authorized_store_ids"]),
            "authorization",
            f"Resultado fora do escopo permitido: {result['scope']}",
        )
        require(result["timezone"] == "America/Sao_Paulo", "query", "Fuso do resultado incorreto.")
        require(result["currency"] == "BRL", "presentation", "Moeda do resultado incorreta.")
        require(result["dataset_version"] == "manual-v1", "query", "Versão dos dados incorreta.")
        require(bool(result["formula"]), "presentation", "Fórmula ausente.")
        require(bool(result["request_id"]), "presentation", "Request ID ausente.")
        if case["mode"] != "structured":
            require(
                result["request_id"] == payload["request_id"],
                "presentation",
                "Request ID da resposta difere da evidência.",
            )
            if payload.get("plan"):
                assert_subset(result["period"], payload["plan"]["period"], "period", "query")
    if expected.get("comparison_unavailable"):
        require(result is not None, "query", "Resultado ausente.")
        comparison = result["comparison"]
        require(
            comparison is None
            or (comparison["change_percent"] is None and comparison["value"] is None),
            "query",
            f"Comparação com cobertura incompatível deveria estar indisponível: {comparison}",
        )
    return {
        "http_status": response.status_code,
        "status": payload.get("status"),
        "value": result.get("value") if result else None,
        "request_id": payload.get("request_id"),
    }
