# Testes locais

Para a publicação, a instalação e as suítes foram repetidas em uma cópia somente com arquivos Git, agora em Python 3.12.14 e imagens Alpine. Os 313 testes backend, 57 avaliações e 47 casos Playwright passaram. Consulte a [revalidação e correções](publication-check.md). Os registros abaixo preservam a execução anterior e sua configuração.

Execução de 21/09/2026 UTC, Windows/PowerShell 7 e containers Linux: Python 3.12.12, Node 24.19.0 e PostgreSQL 17.11. Locks: `backend/uv.lock` e `frontend/package-lock.json`. Execute os comandos na raiz do clone.

## Comandos e resultados

| Comando | Resultado |
|---|---|
| `docker compose build backend` e `docker compose build frontend` | Imagens construídas; Next.js compilou versão de produção. [Backend](evidence/azure-live/backend-build.log), [frontend](evidence/problem-review/frontend-build-final.log). |
| `docker compose --profile test run --rm test` | Ruff, formato e mypy passaram; 313 testes backend em 18,05 s, incluindo as 57 avaliações de regressão (57/57 também no runner). [Log](evidence/azure-live/backend-checks.log), [avaliações](../evals/reports/latest.md), [JSON](../evals/reports/latest.json). |
| `pwsh -NoProfile -File scripts/dev.ps1 check-frontend` | ESLint, TypeScript e Prettier passaram. [Log](evidence/problem-review/frontend-checks.log). |
| `pwsh -NoProfile -File scripts/dev.ps1 e2e` | 47 casos Playwright em 38,3 s: 28 jornadas de aplicação/HTTP e 19 casos puros, sem skip ou retry, em outro Compose com banco novo/tmpfs, migração/seed e proxy reais. [Log](evidence/problem-review/e2e.log). O frontend não mudou na integração Azure. |
| `docker compose --profile evaluation run --rm evaluator python -m evals.live_runner --mode offline --stage development` | Parser 12/12 e consulta estruturada 9/9 nos casos aplicáveis, com valores manuais, FastAPI e PostgreSQL real; três recusas não se aplicam ao formulário estruturado. [Relatório](../evals/reports/20260921T063624Z-d4d4fcdb/summary.md). Zero chamadas a modelo. |
| `python scripts/verify_evidence.py` | Confere hashes dos arquivos publicados, contagens, chamadas, tokens e custo estimado, sem rede. |

Avaliação com modelo real no Azure Foundry: smoke, desenvolvimento e final, 47/48 no caminho modelo + backend, 42 chamadas reais e seis guardas locais, 55 chamadas no total e custo estimado US$ 0,01550395. Detalhes, fontes congeladas e falha registrada em [azure-live-results.md](azure-live-results.md); logs em [evidence/azure-live/README.md](evidence/azure-live/README.md). Resultados anteriores à integração Azure ficam em [evidence/problem-review/README.md](evidence/problem-review/README.md).

O SDK foi exercitado por transporte simulado para rota Azure v1, deployment, schema, falhas, IDs e tokens; dois testes atravessam a aplicação e o PostgreSQL. O plano autorizado retorna 3.000 centavos/2 pedidos/8 unidades; o plano de outra organização retorna 403 sem SQL de vendas. Reservas sobrevivem a reinício e a cópias da autorização; excesso medido bloqueia novas chamadas mesmo se o processo interromper antes de gravar um marcador auxiliar. A [captura](screenshots/language-proof.png) e a jornada com paráfrases verificam o mesmo cálculo e recusam qualificadores ausentes.

Um aviso externo Starlette/AnyIO (`BlockingPortal`) permanece visível. O workflow de CI tem `permissions: contents: read` e roda os mesmos comandos do Compose local.

## Casos testados

| Área | Testes |
|---|---|
| Cálculo | Valores esperados calculados à mão: múltiplos itens, dinheiro/ticket sem arredondamento duplo, pedidos distintos, empate, UTC/São Paulo e fim exclusivo. |
| Cobertura | Zero somente em dia carregado, ausência com null, parcial exclui vendas sem cobertura e impede comparação completa. |
| Autorização | Sessão, logout, expiração, Origin/CSRF independentes, tenant vindo da sessão, lojas mistas e planos maliciosos; listener verifica ausência de SQL proibido; FK composta protege joins. |
| Histórico revogado | Consulta Jardins seguida de Centro; revogar Jardins remove título/ID da lista e recusa detalhe. |
| Qualificadores | Pagamento, vendedor, categoria, produto, canal, horários e números não reconhecidos, exclusões e ambiguidades pedem esclarecimento sem SQL de vendas. Guarda LLM impede SDK. |
| Corpo HTTP e dinheiro | API/proxy recusam mais de 16 KiB antes do decode, inclusive chunks sem Content-Length correto. Centavos acima de 2^53 e multiplicação de BIGINT por INTEGER atravessam PostgreSQL, JSON, histórico legado e formatação exata. |
| Concorrência | Duas conexões reais: mesma conversa bloqueada gera 409; após commit funciona. Não mede vazão. |
| Provedor | SDK real com transporte simulado: schema estrito, campos proibidos, recusa, incompleta, rate limit e timeout. A qualidade semântica é medida só na avaliação Azure. |
| Navegador | Consulta/cálculo, ranking, comparação/continuação, troca de usuário com requisições diretas a IDs alheios, histórico tardio, teclado, estados, contraste automatizado e reflow. |

As 57 avaliações estão incluídas nos 313 testes pytest. No Playwright, 19 dos 47 casos são puros; a execução terminou sem skip, retry ou flaky.

## Capturas e acessibilidade

Capturas da aplicação no E2E isolado: [início](screenshots/inicio.png), [consulta com cálculo](screenshots/consulta-com-evidencia.png), [evolução](screenshots/evolucao-diaria.png), [outra organização](screenshots/organizacao-b.png), [celular](screenshots/consulta-mobile.png). A consulta principal parte de histórico com uma conversa; capturas posteriores mostram somente a sequência temporária da suíte.

Em [1280×720](screenshots/welcome-1280x720.png), seis atalhos cabem antes do campo de pergunta. Em [390×844](screenshots/welcome-390x844.png), o teste exige pelo menos quatro.

As [medições](screenshots/viewport-checks.json) verificam o painel Cálculo aberto em 1440×900, 1366×768, 768×1024, 390×844, 320×844 e 320×256 CSS px: sem overflow horizontal global, campo focado acessível, tabelas com rolagem própria. Menu responde a Escape/devolve foco; redução de movimento respeitada. Axe não encontrou violações nos estados exercitados. 320×256 reproduz geometria equivalente a 400%, mas zoom nativo não foi medido.

## Dados e operação

A migração 0002 promoveu o CHECK de preço × quantidade para NUMERIC, sem reescrever dados; contagens e SHA-256 de pedidos, itens, cobertura, conversas e respostas ficaram iguais antes e depois. No instante da comparação: 6.316 pedidos, 15.683 itens, 538 coberturas, 67 conversas e 108 respostas; novas consultas manuais podem aumentar o histórico depois. Backup local em `.runtime` está ignorado. Só `plpgsql` estava instalada.

E2E tem projeto/rede/segredo/DB próprios, sem portas host; backend pytest usa um terceiro banco com sufixo `_test`, validado antes de migrar. Script E2E limpa em `finally` somente esse ambiente, inclusive na falha. Nenhum histórico demo foi apagado. Não há cache entre usuários.

`/operations` mede serviço até gravar registro, excluindo commit/rede; falhas que impedem persistir aparecem apenas em logs sanitizados. Não há custo/tokens medidos, teste de carga ou recuperação de desastre. [EXPLAIN](query-plan.md) e setup inicial foram registrados em PostgreSQL 17.6: contexto histórico, não benchmark atual.

[Organização da interface](quality-review.md).
