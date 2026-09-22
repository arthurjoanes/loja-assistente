import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from loja_assistente.analytics.contracts import Totals
from loja_assistente.models import AnswerRecord, OrderItem


@pytest.mark.parametrize(
    "price,quantity,expected",
    [
        (9_007_199_254_740_993, 1, "9007199254742993"),
        (9_223_372_036_854_775_807, 2, "18446744073709553614"),
        (9_223_372_036_854_775_807, 2_147_483_647, "19807040619342712359383730129"),
    ],
)
def test_large_cents_survive_query_history_and_evidence(
    price: int, quantity: int, expected: str, db: Session, manager_client: TestClient
) -> None:
    item = db.get(OrderItem, ("org_a", "oa4-item-0"))
    assert item is not None
    item.unit_price_cents = price
    item.quantity = quantity
    db.commit()
    reply = manager_client.post(
        "/api/assistant/query", json={"question": "Evolucao diaria da receita ontem"}
    )
    assert reply.status_code == 200
    answer = reply.json()
    assert answer["result"]["value"] == expected
    assert answer["result"]["totals"]["revenue_cents"] == expected
    assert answer["result"]["rows"][0]["revenue_cents"] == expected
    assert answer["result"]["evidence"][0]["revenue_cents"] == expected
    evidence = manager_client.get(f"/api/answers/{answer['id']}/evidence")
    assert evidence.json()["rows"][0]["revenue_cents"] == expected
    stored = db.get(AnswerRecord, answer["id"])
    assert stored is not None
    # Historical payloads used JSON integers. The server upgrades representation when reading.
    legacy = dict(stored.payload)
    legacy["result"]["totals"]["revenue_cents"] = int(expected)
    legacy["result"]["rows"][0]["revenue_cents"] = int(expected)
    legacy["result"]["evidence"][0]["revenue_cents"] = int(expected)
    from sqlalchemy.orm.attributes import flag_modified

    stored.payload = legacy
    flag_modified(stored, "payload")
    db.commit()
    history = manager_client.get(f"/api/conversations/{answer['conversation_id']}").json()
    assert history["messages"][0]["result"]["totals"]["revenue_cents"] == expected


def test_response_schema_documents_cents_as_text() -> None:
    schema = Totals.model_json_schema(mode="serialization")
    assert schema["properties"]["revenue_cents"]["type"] == "string"
