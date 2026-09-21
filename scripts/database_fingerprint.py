"Calcula hashes do banco antes e depois de uma manutenção."

import hashlib
import json

from sqlalchemy import select, text

from loja_assistente.database import engine
from loja_assistente.models import AnswerRecord, Conversation, Coverage, Order, OrderItem


def main() -> None:
    report = {}
    with engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection:
        connection.execute(text("SET TRANSACTION READ ONLY"))
        for model in (Order, OrderItem, Coverage, Conversation, AnswerRecord):
            table = model.__table__
            digest = hashlib.sha256()
            count = 0
            for row in connection.execute(select(table).order_by(*table.primary_key.columns)):
                digest.update(json.dumps(dict(row._mapping), default=str, sort_keys=True).encode())
                count += 1
            report[table.name] = {"count": count, "sha256": digest.hexdigest()}
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
