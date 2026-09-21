# Testes locais

## Azure Foundry — integração real de 21/09/2026

[Relatório atual](azure-live-results.md): 313 testes backend em 18,05 s, Ruff/formato/mypy e 57/57 regressões; smoke, desenvolvimento e final com modelo real. Final 47/48 no caminho modelo + backend, 42 chamadas reais e seis guardas locais. Zero falhas críticas; um esclarecimento desnecessário. 55 chamadas no total das três etapas, custo conservador US$ 0,01550395. Fonte, IDs, tokens, falhas e contratos congelados estão vinculados no relatório.

A preparação descrita a seguir é histórica, anterior à entrega do endpoint e à autorização de US$ 15.

Revisão em **21/09/2026 UTC**, Windows/PowerShell 7 e containers Linux: Python 3.12.12, Node 24.19.0 e **PostgreSQL 17.11**. Locks: `backend/uv.lock` e `frontend/package-lock.json`. Execute os comandos na raiz do clone.

## Revisão do problema e da prova

[Índice da execução e tentativas preservadas](evidence/problem-review/README.md). A suíte atual passou **305 testes backend** em 18,54 s, incluindo as 57 avaliações anteriores; execução explícita dessas avaliações também passou 57/57. Ruff/formato (49 arquivos) e mypy (33 módulos) passaram. ESLint, TypeScript e Prettier passaram. Chromium passou **47 casos em 38,3 s: 28 jornadas de aplicação/HTTP e 19 casos puros**, sem skip ou retry.

O novo [comparador offline](../evals/reports/20260921T063624Z-d4d4fcdb/summary.md) executou 12 casos de desenvolvimento por parser e nove consultas estruturadas aplicáveis, com valores manuais, FastAPI e PostgreSQL real. Todos passaram. Três recusas não se aplicam ao formulário estruturado e continuam no denominador do parser. Essa amostra conhecida não mede generalização de um modelo nem produtividade de pessoas. Estado: `offline_only`; chamadas a modelo: **zero**.

O SDK foi exercitado por transporte simulado para rota Azure v1, deployment, schema, falhas, IDs e tokens; dois testes atravessam a aplicação e o PostgreSQL. O plano autorizado retorna 3.000 centavos/2 pedidos/8 unidades; o plano de outra organização retorna 403 sem SQL de vendas. Reservas sobrevivem a reinício e a cópias da autorização; excesso medido bloqueia novas chamadas mesmo se o processo interromper antes de gravar um marcador auxiliar. A [captura real](screenshots/language-proof.png) e a jornada com paráfrases verificam o mesmo cálculo e recusam qualificadores ausentes.

A avaliação live permanece pendente de deployment e orçamento. Protocolo, comandos e limites: [live-evaluation.md](live-evaluation.md). As seções seguintes preservam a revisão anterior; suas contagens não são a rodada atual.

## Comandos da revisão anterior

| Comando | Resultado |
|---|---|
| `docker compose build backend` e `docker compose build frontend` | Imagens construídas; Next.js compilou versão de produção. |
| `docker compose --profile test run --rm test` | Ruff e formato: 46 arquivos; mypy: 32 módulos; **262 testes** e **57/57 avaliações** passaram. [Log](round-2-backend.txt), [avaliações](../evals/reports/latest.md), [JSON](../evals/reports/latest.json). |
| `docker compose --profile test build frontend-check` e `docker compose --profile test run --rm frontend-check` | ESLint, TypeScript e Prettier passaram. [Log](round-2-frontend.txt). |
| `pwsh -NoProfile -File scripts/dev.ps1 e2e` | **46 casos Playwright: 27 jornadas de aplicação/HTTP e 19 casos puros** em outro Compose: banco novo/tmpfs, migração/seed e proxy reais, limpeza própria ao terminar. [Log](round-2-e2e.txt). |
| `docker compose --profile test run --rm --no-deps frontend-check npm audit --json` | Scan da primeira revisão no mesmo dia; mesmos locks, nenhum advisory reportado, runtime e tooling incluídos. [JSON](review-npm-audit.json). |
| `docker compose run --rm --no-deps backend uv tool run pip-audit --path /opt/venv/lib/python3.12/site-packages --format json` | Scan da primeira revisão no mesmo dia, sem alteração do lock: nenhuma vulnerabilidade conhecida no ambiente Python resolvido, incluindo dev tools. [JSON](review-pip-audit.json). Scanner efêmero, sem alterar pacotes. |
| `docker compose run --rm --no-deps backend python /app/scripts/database_fingerprint.py` antes/depois da migração 0002 | Contagens e SHA-256 idênticos em pedidos, itens, cobertura, conversas e respostas. [Antes](round-2-db-before.json), [depois](round-2-db-after.json). |
| `docker compose up -d --wait db backend frontend` | Saudáveis. GET 3102: 200; API 8102/api/health: 200/status ok. SHOW server_version: 17.11. |

Um aviso externo Starlette/AnyIO (`BlockingPortal`) permanece visível. Scans de pacotes não são auditoria das camadas de sistema operacional das imagens. Workflow tem `permissions: contents: read`; **GitHub Actions hospedado ainda não foi executado**.

## Casos testados

| Área | Testes |
|---|---|
| Cálculo | Oráculo manual independente: múltiplos itens, dinheiro/ticket sem arredondamento duplo, pedidos distintos, empate, UTC/São Paulo e fim exclusivo. |
| Cobertura | Zero somente em dia carregado, ausência com null, parcial exclui vendas sem cobertura e impede comparação completa. |
| Autorização | Sessão, logout, expiração, Origin/CSRF independentes, tenant vindo da sessão, lojas mistas e planos maliciosos; listener comprova ausência de SQL proibido; FK composta protege joins. |
| Histórico revogado | Consulta Jardins seguida de Centro; revogar Jardins remove título/ID da lista e recusa detalhe. |
| Qualificadores | Pagamento, vendedor, categoria, produto, canal, horários e números não reconhecidos, exclusões e ambiguidades pedem esclarecimento sem SQL de vendas. Guarda LLM impede SDK. |
| Corpo HTTP e dinheiro | API/proxy recusam mais de 16 KiB antes do decode, inclusive chunks sem Content-Length correto. Centavos acima de 2^53 e multiplicação de BIGINT por INTEGER atravessam PostgreSQL, JSON, histórico legado e formatação exata. |
| Concorrência | Duas conexões reais: mesma conversa bloqueada gera 409; após commit funciona. Não mede vazão. |
| Provedor | SDK real com transporte simulado: schema estrito, campos proibidos, recusa, incompleta, rate limit e timeout. Nenhuma chamada paga ou qualidade semântica ao vivo. |
| Navegador | Consulta/evidência, ranking, comparação/continuação, troca de usuário com requisições diretas a IDs alheios, histórico tardio, teclado, estados, contraste automatizado e reflow. |

As 57 avaliações estão incluídas nos 262 testes pytest. No Playwright, 19 dos 46 casos são puros; a execução terminou sem skip, retry ou flaky.

## Capturas e acessibilidade

Capturas atuais da aplicação no E2E isolado: [início](screenshots/inicio.png), [consulta com evidência](screenshots/consulta-com-evidencia.png), [evolução](screenshots/evolucao-diaria.png), [outra organização](screenshots/organizacao-b.png), [celular](screenshots/consulta-mobile.png). A consulta principal parte de histórico com uma conversa; capturas posteriores mostram somente a sequência temporária da suíte.

Em [1280×720](screenshots/welcome-1280x720.png), seis atalhos cabem antes do campo de pergunta. Em [390×844](screenshots/welcome-390x844.png), o teste exige pelo menos quatro.

As [medições](screenshots/viewport-checks.json) verificam evidência aberta em 1440×900, 1366×768, 768×1024, 390×844, 320×844 e 320×256 CSS px: sem overflow horizontal global, campo focado acessível, tabelas com rolagem própria. Menu responde a Escape/devolve foco; redução de movimento respeitada. Axe sem violações nos estados exercitados não certifica WCAG. **320×256 reproduz geometria equivalente a 400%, mas zoom nativo não foi medido.**

## Dados e operação

A manutenção anterior 17.6 → 17.11 manteve o volume. Nesta rodada, a migração 0002 promoveu o CHECK de preço × quantidade para NUMERIC, sem reescrever dados. No instante da comparação: 6.316 pedidos, 15.683 itens, 538 coberturas, 67 conversas e 108 respostas; novas consultas manuais podem aumentar histórico depois. Backup local em `.runtime` está ignorado. Só `plpgsql` estava instalada; ressalvas oficiais de extensões foram conferidas.

E2E tem projeto/rede/segredo/DB próprios, sem portas host; backend pytest usa um terceiro banco com sufixo `_test`, validado antes de migrar. Script E2E limpa em `finally` somente esse ambiente, inclusive na falha. Nenhum histórico demo foi apagado. Não há cache entre usuários.

`/operations` mede serviço até gravar registro, excluindo commit/rede; falhas que impedem persistir aparecem apenas em logs sanitizados. Não há custo/tokens medidos, teste de carga ou recuperação de desastre. [EXPLAIN](query-plan.md) e setup inicial foram registrados em 17.6: contexto histórico, não benchmark atual.

[Matriz de campos e revisão técnica](review-round-2.md). [Publicação](publishing.md).
