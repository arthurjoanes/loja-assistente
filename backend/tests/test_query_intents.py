from unittest.mock import Mock

from sqlalchemy import func, select

from loja_assistente.assistant import service
from loja_assistente.models import AnswerRecord, QueryIntent


def test_lost_response_replay_recovers_one_answer_without_reinterpreting(
    manager_client, db, monkeypatch
):
    interpretation = Mock(wraps=service.interpret_request)
    monkeypatch.setattr(service, "interpret_request", interpretation)
    body = {"question": "Quanto vendi ontem?", "mode": "demo", "client_request_id": "lost-response"}
    first = manager_client.post("/api/assistant/query", json=body)
    assert first.status_code == 200, first.text
    replay = manager_client.post("/api/assistant/query", json=body)
    assert replay.status_code == 200, replay.text
    assert replay.json() == first.json()
    assert interpretation.call_count == 1
    assert db.scalar(select(func.count()).select_from(AnswerRecord)) == 1
    recovered = manager_client.get("/api/assistant/requests/lost-response")
    assert recovered.json() == first.json()
    assert (
        manager_client.post(
            "/api/assistant/query", json=body | {"question": "Pedidos ontem?"}
        ).status_code
        == 409
    )
    assert (
        manager_client.post(
            "/api/assistant/query", json=body | {"client_request_id": "explicit-new"}
        ).status_code
        == 200
    )
    assert interpretation.call_count == 2


def test_crash_after_admission_never_repeats_interpretation(manager_client, db, monkeypatch):
    interpretation = Mock(side_effect=RuntimeError("controlled crash before publication"))
    monkeypatch.setattr(service, "interpret_request", interpretation)
    body = {"question": "Quanto vendi ontem?", "client_request_id": "uncertain"}
    assert manager_client.post("/api/assistant/query", json=body).status_code == 500
    db.rollback()
    assert manager_client.post("/api/assistant/query", json=body).status_code == 409
    assert manager_client.get("/api/assistant/requests/uncertain").status_code == 409
    assert interpretation.call_count == 1
    assert db.scalar(select(func.count()).select_from(QueryIntent)) == 1
