# Avaliações

## Interpretação natural e Azure

`live_runner.py` compara demo, plano estruturado e, somente com autorização, o modelo real. Usa `development-v1.json` (12 casos) e `final-v1.json` (24 casos escritos antes do freeze e só executados depois, duas repetições). A avaliação Azure de 21/09/2026 foi aprovada: 47/48 no caminho modelo + backend, contra 24/48 do parser. [Resultados e limites](../docs/azure-live-results.md), [tabela por pergunta](../docs/evidence/azure-live/cases.md) e [chamadas com tokens](../docs/evidence/azure-live/calls.md).

O holdout dessa avaliação já está publicado e deve ser tratado como regressão em trabalhos futuros. Uma nova avaliação exige novos casos e novo freeze. Freeze das fontes/casos, uso medido, reserva persistente e comandos em [live-evaluation.md](../docs/live-evaluation.md). O modo padrão continua offline.

`reports/<UTC-id>/` preserva cada execução, esperado/observado, falhas e hashes; o resumo não sobrescreve outra execução. A suíte abaixo continua verificando regressões de segurança/financeiro e declara seus modos simulados.

| Execução preservada | Natureza | Relatório |
|---|---|---|
| `20260921T063624Z-d4d4fcdb` | Preparação offline, sem inferência | [Resumo](reports/20260921T063624Z-d4d4fcdb/summary.md) |
| `20260921T121119Z-883376fa` | Smoke Azure, 1 chamada | [Resumo](reports/20260921T121119Z-883376fa/summary.md) |
| `20260921T121149Z-c53a402a` | Desenvolvimento Azure, 12 chamadas | [Resumo](reports/20260921T121149Z-c53a402a/summary.md) |
| `20260921T121255Z-a9c11d1f` | Final Azure, 42 chamadas + 6 guardas locais | [Resumo](reports/20260921T121255Z-a9c11d1f/summary.md) |

Para conferir os arquivos publicados sem chave ou chamadas pagas: `python scripts/verify_evidence.py`. Para regenerar somente as tabelas a partir dos JSONL existentes: `python scripts/render_evidence.py --write`.

`cases/manual-v1.json` contém 57 casos com identidade, pergunta e resultados esperados. Os valores são calculados à mão, conforme a [fixture](../docs/manual-fixture.md).

Cada caso passa por login e HTTP real do FastAPI via TestClient, usando PostgreSQL real. Os modos do relatório distinguem:

- demo: interpretação pelo parser determinístico, autorização, consulta, cálculo e apresentação.
- structured: contrato HTTP de consultas estruturadas; entradas proibidas, limites e números.
- interpreter_stub: saída maliciosa bem formada simulada, seguida do fluxo real de autorização. Não mede qualidade de um LLM.

O runner usa exclusivamente TEST_DATABASE_URL com banco PostgreSQL cujo nome termina em _test. Aplica as migrações Alembic reais e popula dados dentro de transação externa revertida ao encerrar; um banco com usuários existentes é recusado. O Compose fornece banco efêmero isolado da demonstração. Conftest e runner compartilham a preparação do banco; não usam create_all nem stamp.

Execução no serviço de testes:

~~~text
docker compose --profile test up -d test-db
docker compose --profile test run --rm test python /app/evals/runner.py --output-dir /app/evals/reports/local
~~~

No pytest, os mesmos casos são parametrizados em backend/tests/test_evals.py. Testes adicionais em test_security.py exercitam a barreira de acesso aos dados, CSRF, relógio de expiração, duas sessões alternadas, revogação, respostas/cálculos/histórico pessoais e colisões de IDs. Os contratos do adaptador LLM têm testes específicos separados.

O comando grava `reports/local/latest.json` e `reports/local/latest.md`, ignorados pelo Git, com data, ambiente e resultado por caso. Os atalhos `dev.ps1 test` e `dev.ps1 eval` usam o mesmo diretório, preservando os relatórios históricos verificados por `verify_evidence.py`. Ao chamar o runner diretamente, informe `--output-dir`: o default histórico `reports/` sobrescreve os arquivos `latest.*` publicados. `category` agrupa o caso; `failure_stage` indica a checagem que falhou. Exceções sem classificação usam `infrastructure/unknown`. O processo retorna 1 se algum caso falhar.

Os testes usam o parser demo e transporte simulado. Não chamam o LLM.
