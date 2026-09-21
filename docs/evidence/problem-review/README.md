# Testes locais anteriores à avaliação Azure

Execução de 21/09/2026 UTC. A avaliação Azure posterior, com modelo real, está em [azure-live-results.md](../../azure-live-results.md). Este índice guarda os logs locais anteriores à autorização do gasto. Dados sintéticos, nenhuma chamada a modelo e nenhuma medição com usuários. Fontes sem commit: fingerprints por arquivo no manifest do comparador e no freeze.

| Comando | Resultado e log |
|---|---|
| Função do parser na imagem que estava em execução | [Baseline v3](parser-before.json), 05:52:30 UTC: pergunta canônica aceita; pronome/cortesia rejeitados. Não consulta nem altera o banco. |
| `docker compose --profile test run --rm test` | [Terceira tentativa](backend-checks-3.log), [horário/comando/exit code](backend-checks-3.json): Ruff/formato/mypy, migrações, 305 pytest em 18,54 s; 57/57 avaliações já incluídas no pytest também passaram no runner. |
| `pwsh -NoProfile -File scripts/dev.ps1 check-frontend` | [Log](frontend-checks.log): build da imagem de checks, ESLint, TypeScript e Prettier; exit 0. |
| `pwsh -NoProfile -File scripts/dev.ps1 e2e` | [Log](e2e.log): builds, migração/seed exclusivos, proxy e Chromium; 47/47 em 38,3 s, sem skip/retry; exit 0 e limpeza do Compose `pf-loja-assistente-e2e`. 28 jornadas/19 casos puros. |
| `docker compose --profile evaluation run --rm evaluator python -m evals.live_runner --mode offline --stage development` | [Horário/comando/exit](offline-development.json), [log](offline-development.log), [relatório](../../../evals/reports/20260921T063624Z-d4d4fcdb/summary.md): parser 12/12, estruturado 9/9; três recusas não aplicáveis ao formulário. |
| Builds finais, atualização preservando volume e `--freeze` | [Registro](refresh.json), [log do freeze](freeze.log), [contrato congelado](../../../evals/freeze.json), [imagens em execução](runtime-images.json). API e frontend saudáveis; exit 0, zero chamadas live. |

No relatório do comparador, `cases.jsonl` contém entrada sintética, esperado e observado, consultas analíticas e avaliação por caso. `manifest.json` identifica Python 3.12.12, PostgreSQL 17.11, OpenAI SDK 3.16.2, fonte, contratos e comando. Transporte FastAPI/ASGI; o teste pelo proxy está na suíte E2E. p95 local inclui login sintético: 184 ms no parser e 68 ms na consulta estruturada; não é benchmark de produção nem comparação de produtividade.

Falhas anteriores preservadas: [primeira tentativa](backend-checks.log) parou no formatter de `demo_language.py`; [segunda](backend-checks-2.log) teve 302 aprovados/1 falha na expectativa do teste para ticket `1500` versus a representação decimal `1500.00`. O valor financeiro era igual; corrigiu-se a expectativa literal, sem mudar o cálculo.

O adaptador foi testado com transporte simulado e PostgreSQL real: contexto de medição chega ao SDK; plano autorizado calcula 3.000 centavos, dois pedidos e oito unidades, com cálculo persistido igual; plano alheio recebe 403 sem SQL de vendas. Isso não testa semântica de modelo. O ledger tem testes de reserva antes da chamada, concorrência, reinício, cópia de autorização, contrato alterado, uso parcial e excesso medido persistido sem marcador posterior.

A atualização da demo em 06:36:48–06:37:15 UTC preservou contagens e hashes de pedidos (6.316), itens (15.683), cobertura (538), conversas (74) e respostas (118): [antes](demo-before.json), [depois](demo-after.json). Test-db foi parado e E2E removido. O hash dos casos finais permaneceu `558a032290fa926943187c55e2a48ed130d02192dfe3bdc0fa093004d125b128`; as frases só foram abertas depois do freeze. O freeze ocorreu em 06:37:10 UTC e cobre fontes, testes, locks e Compose relevantes ao avaliador; [fingerprint adicional](frontend-and-scripts-fingerprint.json) identifica frontend e scripts.

[Captura da jornada](../../screenshots/language-proof.png): pergunta canônica e paráfrase produzem o mesmo resultado. A suíte verifica também cortesia, filtro não suportado, saudação e recuperação. Os 24 casos finais × duas repetições foram executados depois, no Azure: [resultado](../../azure-live-results.md) e [protocolo](../../live-evaluation.md).
