# Testes locais

## Revisão autoral de portfólio — 22/09/2026

Revisei problema, conta manual, decisões, código e as três capturas reais de `f98ee948…`. A fixture `manual-v1` de R$ 30 permanece separada do caso visual `synthetic-v1` de R$ 10.810,95. O README identifica minhas contribuições e as bibliotecas que integrei; a arquitetura, o orçamento e os contratos não foram alterados.

Construí somente o backend atual, com Dockerfile e locks presentes, em tag própria: **Python 3.12.14**, imagem `sha256:54aa5ebe173e51bb354be5e4ee359fc4e7154040e80f2793ece2d7c0d5881b3e`. `scripts/check.py` passou Ruff, formato (58 arquivos), mypy (36 fontes), migrações até 0003, **364 testes** em 72,01 s e **57/57 casos offline**. Os 364 incluem os 353 da prova anterior e 11 casos de integridade histórica. Um aviso de depreciação do alias AnyIO usado pelo TestClient do Starlette permaneceu visível. O banco era temporário, sem portas; a rede era interna, LLM estava desligado e a chave vazia. Fontes foram montadas somente para leitura, com saída de relatório separada. Esses tempos, com outras tarefas no host, não são benchmark.

Preservei duas falhas de preparação: primeiro o Docker não pôde criar o ponto de montagem do relatório sob a raiz somente para leitura; depois, um endpoint fictício HTTP foi corretamente recusado pela validação de configuração antes de migrar. Criei o diretório vazio de destino e usei a URL de configuração aceita, mantendo chave vazia, modo Demo e rede sem saída. Não alterei código, testes, limiares ou guardas para obter aprovação. A terceira tentativa passou e os recursos próprios foram encerrados, sem apagar volumes alheios.

No host Windows, com Node 24.19.0 e npm 11.17.0, instalei o frontend do lock em diretório novo com `npm ci --no-audit --fund=false`. ESLint, Prettier, build de produção, TypeScript e **39 testes puros** (`domain.spec.ts`/`proxy-streams.spec.ts`, 1,3 s, sem skip/retry) passaram. Esses casos usam o runner Playwright sem abrir navegador nem iniciar servidor. O arquivo de tipos gerado pelo build foi devolvido aos bytes do snapshot, sem mudar fontes de frontend. `npm audit --package-lock-only --json` retornou zero achados em 22/09/2026; isso não cobre o sistema operacional, segredos ou a aplicação.

Gitleaks 8.30.1, com redação integral e a configuração existente, retornou zero achados nos 396 arquivos rastreados/não ignorados do snapshot e nos sete commits alcançáveis (`--all`). A invocação inicial com caminho absoluto não aplicava as exceções existentes por caminho e marcou digests/ID de correlação históricos; conservei a tentativa e corrigi a invocação para caminho relativo, sem acrescentar exceções. Não fiz nova chamada paga ou avaliação de linguagem.

Trivy 0.74.0 retornou **zero vulnerabilidades** na imagem de backend atual, via Docker local, sem filtro de severidade ou exceções. A base de avisos foi atualizada em 22/09/2026 às 07:24 UTC. O scanner manteve avisos sobre Alpine 3.24 fora de sua lista de EOL e termos adicionais em metadados de licença. Esse resultado cobre os pacotes de sistema/Python detectados, não o frontend ou uma implantação.

`python scripts/verify_evidence.py` passou sem escrita ou rede: 65 artefatos, 62 fontes históricas, dois conjuntos de casos, contagens e somas. O verificador identifica as nove fontes alteradas e os 11 módulos posteriores; não transfere 47/48 da avaliação paga para o código atual. Os resultados originais e a falha `final-bf-04` permanecem preservados. O [recibo desta revisão](evidence/portfolio-review-20260922.json) separa instalação, testes, scans e imagens históricas.

**Situação: design aprovado pelo autor em 22/09/2026; validação de execução do frontend atual pendente.** A recusa automática anterior de inicialização continua respeitada, sem repetição nem método alternativo. Nenhuma das 30 jornadas de navegador/HTTP foi executada nesta revisão; não há nova captura ou validação interativa; a aprovação do design pelo autor não substitui esses testes. A prova `f98ee948…` abaixo corresponde à sua versão congelada, anterior à nova marca, fonte e composição descritas em [qualidade do frontend](frontend-quality.md). O procedimento completo `setup/start/e2e` não foi repetido.

## Validação final da candidata de interface

**Registro histórico `f98ee948…`, anterior à direção visual local atual.** A aprovação abaixo não se aplica automaticamente à composição posterior.

A rodada `f98ee94864384422bd835bcabd8f3a11` exercitou o refinamento posterior de alinhamento, contornos/foco, navegação e Enter durante composição IME. Build, lint, formato, tipos e **68 casos** passaram: 38 puros e 30 de navegador/HTTP, em 38,441 s, sem falha, skip ou retry. As três capturas usam a mesma fixture e viewport 1440×1000, com transições concluídas pelo coletor. Os 158 arquivos congelados ficaram estáveis durante a execução; recursos próprios removidos.

O [registro estático anterior](frontend-quality.md) e sua matriz mantêm o escopo da ocasião. Esta nova prova cobre as jornadas executadas e as três capturas; não substitui estudo com pessoas, leitor de tela ou toda a matriz de comparação visual proposta naquele documento.

## Entrega de 22/09/2026 — orçamento e interface verificados

O [índice desta entrega](evidence/operational-proof-20260922/index.json) identifica cada rodada e conserva as falhas. A [história com capturas](operational-story.md) mostra consulta, recusa e nova tentativa válida; o [contrato do orçamento](provider-budget.md) explica problema, escolhas, operação e limites.

| Prova | Resultado e versão |
| --- | --- |
| Backend, rodada `30792079e0d948258f4ab91d767529c0` | 353 testes passaram em 24,486 s, sem erro/falha/skip; migração 0003, Ruff, formato e mypy passaram. |
| Incremento de orçamento, incluído nos 353 | 40 casos novos: 14 de política, 6 de adaptador, 12 de PostgreSQL/API, 3 de preparação da avaliação e 5 do executor. A integração da preparação também usa PostgreSQL; são 13 casos de banco entre esses módulos. |
| Avaliação offline | 57/57; não houve repetição da avaliação Azure paga. |
| Frontend final, rodada `f98ee94864384422bd835bcabd8f3a11` | Build, lint, tipos e formato passaram; 68 verificações Playwright em 38,441 s, sem skip ou retry: 38 puros, 29 jornadas existentes e uma nova história. |
| Associação entre rodadas | Os 100 arquivos anteriores de backend/evals/data permaneceram byte a byte iguais. O teste histórico acrescentado passou em 11 casos host; a rodada final de frontend não reexecutou os 353 casos. |
| Interface e acessibilidade automatizada | Jornadas de seleção, recorte, cobertura, teclado, foco, reflow, sete geometrias e Axe passaram. Três capturas reais conferidas; isso não é estudo com usuários, teste de leitor de tela ou certificação. |

O provedor dos testes de orçamento usa `httpx.MockTransport`. Foram conferidos oito concorrentes para duas admissões, reserva incerta após timeout, leitura do mesmo saldo por outro processo, rollback da resposta sem restituição, isolamento e reconciliação idempotente. O subprocesso lê o ledger; não é um restart completo da API. O índice separa observações auxiliares de saldo da autoridade dos resultados JUnit.

As tentativas anteriores preservam falha de permissão do cache, uma expectativa incorreta do teste de rollback, contraste insuficiente, seletor antigo de mensagem e rolagem/foco. A aprovação corresponde à última fonte validada para cada componente, com hashes e diferenças registrados. O runtime usou rede interna, credenciais sintéticas e nenhuma porta publicada; cleanup encerrou apenas os recursos próprios. Rodadas anteriores observaram um serviço externo; a última teve snapshots Docker vazios antes/depois. Outras cargas do host não foram controladas; durações não são benchmark de desempenho.

O [arquivo histórico](evidence/azure-live/historical-source-20260921.json) conserva 62 fontes e dois conjuntos de casos originais; o verificador exige esse inventário exato, recusa alteração/ausência/escape de caminho e preserva os 65 artefatos originais. O [suplemento](evidence/operational-proof-20260922/historical-source-supplement.json) registra 11 testes host e os controles de CLI, sem nova chamada paga.

A avaliação histórica de linguagem, os scans anteriores e a auditoria adversarial incompleta mantêm seus próprios escopos. O [protocolo com pessoas](usage-comparison.md) foi preparado, sem participantes ou resultados.

## Histórico da revisão da interface — estado anterior à prova completa

Os parágrafos desta seção registram a etapa parcial que precedeu a entrega acima. Suas pendências de navegador foram tratadas na prova posterior; foram encerradas naquela versão. A direção visual local posterior tem novas jornadas pendentes, descritas em [qualidade do frontend](frontend-quality.md).

A interface passou a exibir um resultado selecionado por vez, com histórico,
filtros, gráfico/tabela e cálculo preservados. Build de produção Next.js,
TypeScript, ESLint, Prettier e 38 testes puros de domínio/transporte passaram
(35 existentes e três casos de apresentação da série diária de 1, 7 e 30 dias).
O verificador offline confirmou os 65 artefatos e 62 fontes congeladas da
avaliação histórica, sem novas chamadas ao modelo.

A composição foi reconstruída novamente nesta revisão: barra superior com
histórico recolhível, controles da próxima consulta em coluna própria, resultado
central, indicadores em faixa, gráfico diário em colunas e login em ficha
centralizada. A descrição textual redundante é consultável sob demanda. As
capturas anteriores e a inspeção preliminar não mostram essa reconstrução.

O refinamento seguinte simplificou os títulos, distribuiu a série diária pela
largura disponível e tornou o formulário recolhível até 1024 px. A pergunta é
o título do resultado; seleção, recorte aplicado e cobertura foram preservados.
Os casos puros verificam que a geometria não descarta dias nem converte os valores
exatos da tabela, e que uma data sem linha mantém uma lacuna em vez de venda zero.
Eles não verificam renderização, foco ou acessibilidade visual. As jornadas
existentes foram ampliadas para conferir 1/7/30 dias, 1024 px, abertura/recolhimento
do formulário com foco e tabela exata, sem reduzir os checks de sobreposição.

Na limpeza posterior, foram retiradas somente as variáveis CSS `--surface` e
`--danger`, sem consumidores nas fontes da interface. Seletores, declarações
consumidas, implementação TypeScript e testes foram preservados. A verificação
de formato confere essa edição; os resultados de build e testes acima pertencem
à revisão imediatamente anterior, sem nova execução de navegador.

Estão pendentes 29 jornadas de navegador/HTTP: as 28 existentes e a regressão
da seleção de resultados, que verifica teclado, preservação da tabela e
continuação pelo último plano válido. Também faltam as capturas finais de
desktop, 1024, 768, 390 e 320 px e a conferência de teclado/reflow a 200% em produção.
As imagens versionadas ainda mostram a interface anterior. A inspeção preliminar
da nova interface em desenvolvimento não substitui esses checks.

A revisão estática também posicionou o carregamento antes do resultado anterior,
levou a rolagem ao aviso de erro e tornou o destino do atalho de conteúdo
focável. Build, ESLint e Prettier passaram após esses ajustes. As asserções de
visibilidade do carregamento/erro e de foco foram acrescentadas às jornadas;
sua execução no navegador permanece pendente.

As jornadas existentes também foram ajustadas à nova composição: os seis/quatro
atalhos de início devem caber no viewport desktop/celular; a navegação de teclado
entra na tabela pelo resumo de Cálculo; os checks de foco visível, hit-test,
ausência de sobreposição e reflow permanecem. O teste de visibilidade dos atalhos
agora mede a tela, em vez de comparar sua posição com o compositor. Nenhuma dessas
asserções foi executada contra a composição reconstruída.

Backend, autorização, cálculo e proxy não foram alterados. Os 313 testes backend
e a avaliação paga pertencem às execuções históricas abaixo; não foram repetidos
nesta revisão de apresentação.

## Revisão de transporte em 22/09/2026 UTC

A correção de deadline/cancelamento do proxy foi validada com build de produção
Next.js e **63 casos Playwright aprovados**, sem skip ou retry: 28 jornadas
existentes de navegador/HTTP e 35 casos puros (19 existentes + 16 novos). A stack
usou banco PostgreSQL novo em tmpfs, seed sintético e `LLM_ENABLED=false`. ESLint,
TypeScript e Prettier passaram. [Detalhes, evidências e limites](security.md).

O verificador dos 65 artefatos, 62 fontes congeladas e duas bases de casos passou
antes/depois, sem escrita nem rede. Os 313 testes backend abaixo pertencem à
execução anterior; esta alteração de frontend não reexecutou a suíte pytest nem
a avaliação paga. As regressões existentes foram preservadas; esta rodada não é
uma nova revisão completa de autenticação/autorização.

## Publicação anterior

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
