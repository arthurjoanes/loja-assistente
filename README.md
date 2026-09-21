# Loja Assistente

Um gestor precisa consultar vendas de suas lojas sem perder filtros, confundir ausência de dados com zero ou receber números de outra organização. O Loja Assistente transforma perguntas em planos limitados, autoriza no servidor e calcula no PostgreSQL, mostrando a mesma evidência usada na resposta. Usa dados fictícios e roda localmente.

![Consulta de vendas](docs/screenshots/consulta-com-evidencia.png)

FastAPI, PostgreSQL, SQLAlchemy/Alembic e Next.js/TypeScript. A [avaliação real com Azure Foundry](docs/azure-live-results.md) obteve **47/48 resultados corretos com GPT-5.6 Luna**, contra 24/48 do parser, em 24 perguntas repetidas duas vezes. Não houve falha crítica nos casos medidos; um esclarecimento desnecessário permanece documentado. A [tese e os critérios](docs/problem-solution.md) explicam a comparação com filtros estruturados e valores calculados à mão.

## Veja a solução e as provas

É possível revisar os resultados no próprio repositório, sem executar o projeto nem fornecer uma chave de IA.

| O que conferir | Onde olhar |
|---|---|
| Problema, decisões e resultado medido | [Resultado Azure e limites da conclusão](docs/azure-live-results.md) |
| Cada pergunta, acertos e a falha preservada | [48 execuções lado a lado](docs/evidence/azure-live/cases.md) |
| Chamadas reais, identificadores e tokens | [55 chamadas à Azure](docs/evidence/azure-live/calls.md) |
| Logs completos, comandos, horários e testes | [Índice de evidências](docs/evidence/README.md) |
| Por que a IA não inventa o total financeiro | [Arquitetura](docs/architecture.md) e [contrato da consulta](backend/src/loja_assistente/analytics/contracts.py) |

A IA interpreta a pergunta; o servidor valida o plano, autoriza o acesso e calcula no PostgreSQL. **Os dados comerciais são sintéticos; as chamadas de modelo foram reais.** O resultado final contém 42 chamadas Azure e seis decisões de guardas locais. Os 313 testes backend e os 47 casos de interface têm logs próprios, identificados por rodada.

```sh
# Confere os arquivos de evidência e recalcula contagens, sem Docker, rede ou API paga.
python scripts/verify_evidence.py
```

O verificador usa apenas a biblioteca padrão do Python 3.11+. Não reexecuta a avaliação de IA. A documentação distingue a [estimativa de consumo](docs/evidence/azure-live/calls.md) da cobrança efetiva, que não foi consultada.

## Executar no Windows

Requer Docker Desktop com engine Linux e PowerShell 7+. O primeiro build baixa imagens e dependências; Node e Python rodam nos containers.

```powershell
# Execute na pasta em que clonou ou extraiu este repositório.
.\scripts\dev.ps1 setup
.\scripts\dev.ps1 start
```

[Aplicação](http://localhost:3102) · [API](http://localhost:8102/docs). O setup cria `.env`, faz o build, aplica a migração e carrega o seed. Repetir o setup mantém dados e configuração.

| Conta fictícia | Escopo |
|---|---|
| `gerente.a@demo.local` | Aurora Casa · Centro (`a001`) |
| `supervisor.a@demo.local` | Aurora Casa · Centro e Jardins (`a001`, `a002`) |
| `gerente.b@demo.local` | Brisa Casa · Centro (`b001`) |

Senha local de todas: **`LojaDemo!2026`**. As contas fictícias só autenticam com `DEMO_MODE=true`. Relógio analítico: **17/08/2026**; “ontem” significa 16/08/2026. Sessões e logs usam o relógio real.

```powershell
.\scripts\dev.ps1 test            # lint, formato, tipos, PostgreSQL e avaliações
.\scripts\dev.ps1 check-frontend  # ESLint, TypeScript e Prettier
.\scripts\dev.ps1 e2e             # jornadas Chromium, celular e acessibilidade
.\scripts\dev.ps1 eval            # relatório de avaliações, sem API paga
.\scripts\dev.ps1 seed            # repete seed sem duplicar
.\scripts\dev.ps1 logs
.\scripts\dev.ps1 stop            # encerra somente este Compose; preserva volume da base
```

Portas em `127.0.0.1`; PostgreSQL sem porta no host. Se 3102/8102 estiverem ocupadas, ajuste `FRONTEND_PORT`/`BACKEND_PORT` no `.env`. Cookie: `la_session`. Compose: `pf-loja-assistente`.

No Linux/CI, `python3 scripts/setup_env.py` cria o `.env`; use `docker compose build backend`, `docker compose build frontend`, `docker compose up -d --wait db`, `docker compose run --rm backend alembic upgrade head`, `docker compose run --rm backend python -m loja_assistente.seed` e `docker compose up -d --wait`. Testes usam `docker compose --profile test run --rm test`; frontend usa `docker compose --profile test build frontend-check` e `docker compose --profile test run --rm frontend-check`.

E2E usa `pf-loja-assistente-e2e`, com banco temporário e LLM desativado. `dev.ps1 e2e` cria e encerra esse ambiente. No Linux:

```sh
docker compose -f compose.e2e.yaml build backend
docker compose -f compose.e2e.yaml build frontend
docker compose -f compose.e2e.yaml build e2e
docker compose -f compose.e2e.yaml up --abort-on-container-exit --exit-code-from e2e
# Execute também se a suíte falhar; remove somente o ambiente E2E.
docker compose -f compose.e2e.yaml down --volumes
```

Encerre o Compose E2E antes de repetir os comandos manuais. Cada execução começa com banco novo. O backend usa outro banco em tmpfs.

## Demo

Entre como gerente A e pergunte “Quanto vendi ontem?”. Abra **Cálculo** para conferir o resultado. [Roteiro](docs/demo.md) e [resultado HTTP](docs/demo-results.json).

## Código

| Tema | Arquivo |
|---|---|
| Caminho da pergunta até o resultado | [assistant/service.py](backend/src/loja_assistente/assistant/service.py) |
| Parser demo | [demo.py](backend/src/loja_assistente/assistant/interpreters/demo.py) e [demo_language.py](backend/src/loja_assistente/assistant/interpreters/demo_language.py) |
| Estado de conversa e sessão na UI | [conversation-state.ts](frontend/src/features/assistant/conversation-state.ts) e [use-workspace.ts](frontend/src/features/assistant/use-workspace.ts) |
| Plano de consulta | [analytics/contracts.py](backend/src/loja_assistente/analytics/contracts.py) |
| Identidade, CSRF e autorização | [auth/service.py](backend/src/loja_assistente/auth/service.py) |
| Cálculo, joins por tenant e cobertura | [analytics/queries.py](backend/src/loja_assistente/analytics/queries.py) |
| Valores calculados à mão | [fixture](docs/manual-fixture.md) |
| Tentativas de acesso e contexto cruzado | [test_security.py](backend/tests/test_security.py) |
| Avaliação real de IA | [comparação por pergunta](docs/evidence/azure-live/cases.md) e [registros originais](evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl) |
| Regressões offline | [relatório](evals/reports/latest.md) e [JSON](evals/reports/latest.json) |
| Plano SQL | [EXPLAIN](docs/query-plan.md) |

[Métricas](docs/metrics.md), [arquitetura](docs/architecture.md), [dados](docs/data-contract.md), [API](docs/api-contract.md), [notas de estudo](docs/interview-guide.md) e [testes](docs/verification.md).

## Limites

“Quanto vendi ontem somente em dinheiro?” pede esclarecimento, sem consultar o total geral. Pagamento, vendedor, categoria, produto individual, horário e exclusões não cabem no plano atual. O modo demo também rejeita termos e números que não reconhece. Cada pergunta escolhe uma métrica principal; “ticket e pedidos” solicita esclarecimento, mesmo que totais auxiliares apareçam em consultas válidas. Exemplos positivos e negativos estão em [demo-parser.md](docs/demo-parser.md) e [test_filter_limits.py](backend/tests/test_filter_limits.py).

O parser demo aceita os [padrões documentados](docs/demo-parser.md). O adaptador foi avaliado ao vivo com GPT-5.6 Luna no Azure Foundry; resultados, custo estimado e limitação estão no [relatório](docs/azure-live-results.md). [Configuração](docs/llm-integration.md) e [avaliação limitada](docs/live-evaluation.md). Testes de protocolo não comprovam compreensão de português; não há ganho de produtividade observado com usuários.

Base com 6.316 pedidos fictícios em 90 dias. Sem lucro, estoque, previsão, impostos ou reembolsos parciais. Comparações exigem cobertura completa. Histórico limitado a 50 conversas e 100 mensagens por conversa, sem paginação.


## Testes

[Revisão Azure atual](docs/azure-live-results.md): 313 testes backend, incluindo 57 avaliações de regressão. A [revisão da interface](docs/evidence/problem-review/README.md) passou 47 casos Playwright (28 jornadas e 19 casos puros). [Comandos e resultados](docs/verification.md). A [segunda revisão](docs/review-round-2.md) permanece como histórico. [Publicação](docs/publishing.md).
