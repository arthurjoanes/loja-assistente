# Avaliação 20260921T121255Z-a9c11d1f

Estado: **live_final_approved**. Etapa: final. Fixture manual-v1; PostgreSQL 17.11 (Debian 17.11-1.pgdg12+2).

| Modo | Casos | Passaram | Falharam | Semântica | p95 ms |
|---|---:|---:|---:|---:|---:|
| demo | 48 | 24 | 24 | 24 | 87 |
| structured | 30 | 30 | 0 | 30 | 79 |
| llm | 48 | 47 | 1 | 47 | 3418 |

Esperado/observado e falhas: cases.jsonl. Schema e fonte: manifest.json. Uso medido e reserva: summary.json.
Latência inclui autenticação sintética e transporte ASGI; não mede navegador, rede do cliente ou produção.
Casos não executados após interrupção permanecem como falha no denominador. Consulta estruturada não se aplica às recusas.
A amostra técnica não mede produtividade de usuários. Transporte simulado não integra esta rodada live.
