# Plano observado da consulta diária

A inspeção histórica executou a consulta SQLAlchemy então vigente do gerente A para Centro (`a001`), de 10/08/2026 incluído a 17/08/2026 exclusivo. A massa `synthetic-v1` continha 6.316 pedidos e 15.683 itens em seis lojas. O artefato registra PostgreSQL **17.6**. Filtros de tenant, loja, status, UTC e cobertura continuam presentes, mas o SQL registrado antecede a promoção de quantidade para `NUMERIC` na [consulta atual](../backend/src/loja_assistente/analytics/queries.py). Não representa um novo plano do código atual.

O [artefato primário](query-plan.json) informa planejamento de **0,54 ms** e execução de **0,438 ms** em `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)`. O JSON não registra a data/hora da medição original. É uma observação local única com caches potencialmente aquecidos, sem caracterização de carga, concorrência ou percentis. Não é benchmark de produção.

Nós observados:

- Aggregate
- Sort
- Nested Loop
- Hash Join
- Index Scan · ix_orders_scope_time · orders
- Hash
- Bitmap Heap Scan · coverage
- Bitmap Index Scan · coverage_pkey
- Index Scan · ix_order_items_order · order_items

O índice composto `ix_orders_scope_time` é definido para tenant, loja e janela temporal; `ix_order_items_order` relaciona itens pelo tenant/pedido. O otimizador pode preferir varreduras sequenciais em tabelas pequenas ou para uma fração elevada das linhas. Não forçamos índices. A associação com cobertura impede interpretar ausência de carga como venda conhecida.

O artefato [query-plan.json](query-plan.json) contém o plano completo, parâmetros, versão do PostgreSQL, buffers e SQL emitido. Para repetir, após setup e seed: `docker compose run --rm backend python /app/scripts/explain.py`. O resultado fica no container; adicione bind da pasta `docs` para persistir no host. A inspeção é somente leitura, exige modo demo e não recebe SQL externo.
