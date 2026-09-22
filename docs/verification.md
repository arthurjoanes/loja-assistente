# Testes locais

## Auditoria final sobre d702d127 — 22/09/2026

Baseline: `origin=https://github.com/arthurjoanes/loja-assistente.git`, branch `main`, SHA `d702d12774bd1c69a58c881eb26058dd2385a41e`, árvore rastreada limpa em 22/09/2026, por volta de 13:00 −03. Inventário: 398 arquivos rastreados, 36 Markdown e 35 PNG/SVG; nenhum novo arquivo não ignorado. `.env`, instruções locais `AGENTS.md`, caches e `.runtime` estavam ignorados. Credenciais existentes não foram copiadas. Foram lidos README, instruções, contratos, arquitetura, decisões, CI e caminhos críticos de autorização, cálculo, orçamento, proxy e estado da interface; testes, scripts e imagens foram amostrados. Inventário não significa leitura de cada fonte histórica.

**Avaliação de contratação:** chamaria para entrevista pelo cálculo com esperado independente, isolamento por organização, reautorização de histórico e reserva de orçamento em transações próprias. A falha reproduzida do avaliador diminuía a confiança no sinal do CI, embora não demonstrasse vazamento do produto. O escopo fechado é proporcional: consultas predefinidas evitam SQL livre; o orçamento só é necessário no caminho opcional com modelo. Uma pergunta técnica útil seria pedir a demonstração de por que o rollback de uma resposta não libera uma chamada já despachada. Qualidade de linguagem aberta, benefício com usuários e operação pública não foram comprovados por esta revisão.

| Requisito | Evidência atual e situação | Correção ou limite |
| --- | --- | --- |
| Dados, domínio e autorização | Conforme nos cenários executados: valores manuais, fuso, cobertura, IDs alheios e ausência de SQL proibido | 373 testes, incluindo nove regressões do avaliador |
| Testes efetivos e CI | Corrigido: avaliação falhava ao encontrar `3300` dentro de um UUID | Metadado validado separadamente; payload financeiro continua recusado |
| UI, hierarquia, estados, teclado e gráficos | Conforme nos percursos automatizados; comparação visual completa não verificada | 30 jornadas/HTTP, sete geometrias; capturas atuais de início desktop, início móvel e cálculo inspecionadas |
| Asserções de geometria/tipografia | Corrigido: laços poderiam passar com coleções vazias | Exigem 12 controles, um campo, três metadados e dois botões de gráfico/tabela |
| Público, problema, exemplo, decisões e limites | Conforme na leitura simulada apenas do README | Conta de R$ 30 completa, cobertura explicada, alternativa com filtros e mapa de manutenção; sem estudo com leitores |
| Fontes e identidade visual | Parcial: fontes primárias e aplicação dos mecanismos conferidas; efeito com pessoas não verificado | Microsoft: esquema JSON; PostgreSQL: precisão; OWASP: permissão a cada acesso. Pesquisa visual anterior é histórica |
| Imagens e provas | Conforme quanto à separação de base manual, massa visual e avaliação histórica | Sem substituir capturas antigas; propostas de design continuam identificadas como simulações |
| Conteúdo público, instalação e manutenção | Conforme no escopo dos checks; implantação pública não verificada | Locks, scans e guia de operação preservados; nenhum commit, push ou deploy |

**Falha preservada e causa:** a rodada inicial `a32041cd926e4ebf827aa3f05afbe3f4` executou 364 testes com sucesso, mas a avaliação seguinte terminou **56/57**, código 1, no caso `user_field_injected`. `evals/harness.py` procurava a substring `3300` no JSON inteiro, incluindo o `request_id` aleatório da resposta 422. O controle determinístico com UUID `33000000-0000-4000-8000-000000000000` reproduziu a mesma falha antes da correção. O ID original daquela resposta não foi gravado pelo relatório; a atribuição desse caso específico à colisão é inferida do caminho 422 e confirmada pelo controle reproduzível, não pela recuperação do ID original.

Agora o avaliador separa somente um `request_id` que seja UUID v4 canônico e inspeciona todos os outros campos, inclusive conteúdo aninhado. Os nove novos testes cobrem o ID sintético no comparador e na API real, valores e organização proibidos, `result`, `totals` e metadados malformados. As guardas de produto, o esperado financeiro e os casos históricos não mudaram. As duas falhas de UI do commit `2e8edd1` e a ausência de `frontend/test-results` no upload **já estavam corrigidas no baseline**; não foram tratadas como defeitos atuais.

**Candidata final:** rodada `0a49ef18a5754dbd8c075b736ba0c489`, fontes congeladas sobre o SHA acima mais as alterações locais, identidade SHA-256 `45a9ed9fb0288defb0abbd08c4669d09b4573fb3a82d18d8583705b3d0af25dc`. Os arquivos de execução permaneceram estáveis. Backend: Ruff, formato, mypy, migrações 0001–0003 e **373 testes**, zero falhas/erros/skips; **57/57** avaliações offline. Frontend: build de produção, ESLint, TypeScript, Prettier e **69 casos Playwright** em 67,107 s, sendo 39 puros e 30 navegador/HTTP, zero falhas/skips/retries. Durações em host compartilhado não são benchmark.

O executor `scripts/prove_budget_ui.py` construiu imagens dos Dockerfiles/locks, com Python 3.12.14, Node 24.19.0, PostgreSQL 17.11 e Playwright 1.63.0. Usou banco novo em memória, rede interna, nenhuma porta publicada, chave vazia e `LLM_ENABLED=false`. A limpeza verificou os dois labels de propriedade antes de encerrar apenas os recursos descartáveis daquela rodada. Serviços das outras auditorias não foram administrados. A instalação Windows `setup/start` e zoom nativo não foram repetidos.

Em uma cópia nova do frontend, `npm ci --no-audit --fund=false` instalou 349 pacotes com cache próprio; `npm audit --package-lock-only --json` retornou zero achados. O npm avisou sobre o ciclo de suporte do ESLint 9 e aprovação de script de instalação do `unrs-resolver`; o fluxo Docker de lint/build passou. Gitleaks 8.30.1, com redação e configuração existente, encontrou zero segredos em 11 commits alcançáveis e nos 398 arquivos rastreados da candidata. Trivy 0.74.0, sem exclusões nem filtro de severidade, retornou zero vulnerabilidades nas imagens backend `4ca2d355ab3e…` e frontend `1666d52bdcb4…`; permanecem os avisos do scanner sobre EOL do Alpine 3.24 e termos de metadados de licença. Esses scans não são pentest.

`python scripts/verify_evidence.py` passou antes e depois: 65 artefatos originais, 62 fontes históricas e dois conjuntos de casos, sem escrita/rede. A falha paga `final-bf-04` e seus números continuam preservados. A checagem final por parser GFM examinou os 36 Markdown sem falha de caminho local ou âncora. O link anônimo do artefato remoto retornou 404, mas a API confirmou `10703737289`, não expirado, com expiração em 21/12/2026; isso não equivale a baixar o ZIP autenticado. O resumo e a captura versionados continuam disponíveis, sem depender desse download.

**Markdown publicado e candidata local:** em 22/09/2026, o README da raiz foi conferido no GitHub no baseline `d702d127…`, incluindo hierarquia, parágrafos, tabelas, código, imagens, textos alternativos, legendas, âncoras e navegação. Em 320 px não houve rolagem horizontal global; tabelas largas mantiveram rolagem na própria região. Essa inspeção pertence à versão publicada, não às edições locais seguintes.

A candidata também foi renderizada em Chromium offline com parser GFM e folhas de estilo obtidas do GitHub. A revisão conjunta dos seis READMEs cobriu 24 combinações: larguras de 1440 e 320 px, temas claro e escuro, quatro por projeto. As imagens carregaram e não houve overflow global; as aberturas e tabelas móveis foram inspecionadas. Esse preview verifica a composição local, mas não reproduz toda a sanitização, navegação ou recursos do GitHub e não comprova publicação da candidata.

A [orientação oficial para README](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes) sustenta a precedência `.github` → raiz → `docs` e a preferência por links relativos internos; a [sintaxe oficial](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax#section-links) explica âncoras e títulos repetidos. Um único título principal, a concisão dos parágrafos e a densidade escolhida de imagens são decisões editoriais desta revisão, não cotas impostas pelo GitHub.

Para reproduzir a prova completa em ambiente com Docker, a partir da raiz, escolhendo uma saída fora do repositório:

```powershell
python scripts/prove_budget_ui.py --output "$env:TEMP/loja-assistente-audit"
```

Os resultados locais brutos ficaram fora do Git; este resumo preserva a falha, o controle reproduzível e o escopo da aprovação. Acesso público ao artefato, comparação visual pareada, leitor de tela, desempenho percebido, backup/restore e implantação continuam sem nova comprovação. A redução de legendas e a posição dos detalhes no README são escolhas editoriais; não são regras de quantidade de imagens ou palavras impostas pelo GitHub.

## CI da interface publicada — 22/09/2026

O [CI do commit `73aa1fff`](https://github.com/arthurjoanes/loja-assistente/actions/runs/35747541226), SHA **`73aa1fff1e061b6f7c562d788544f4c968b50b7e`**, tentativa 1, terminou com sucesso: **69 casos Playwright em 55,626 s**, sendo 39 puros e 30 de navegador/HTTP, sem falha, skip ou retry. Chromium/Playwright 1.63.0, um worker, Next 16.3.5 e React 19.3.0. Build, 364 testes de backend, avaliação offline, frontend checks, demo HTTP, scans e limpeza também passaram. O modo Demo estava ativo, `LLM_ENABLED=false`, chave vazia; `LAYOUT_BASELINE` não estava definido, portanto os checks de reflow/foco foram exigidos.

O resultado preserva duas falhas anteriores. No [run `35745146492`](https://github.com/arthurjoanes/loja-assistente/actions/runs/35745146492), `2e8edd1`, passaram 67 casos e falharam dois: o painel inicial empurrava os atalhos para fora da primeira tela, com zero botões inteiros visíveis onde se exigiam seis em 1280×720 e quatro em 390×844. A preparação foi movida para depois dos atalhos e estes passaram a ocupar duas colunas no celular, mantendo o formulário disponível. No [run `35746622056`](https://github.com/arthurjoanes/loja-assistente/actions/runs/35746622056), `f48941e`, os dois casos passaram; restou uma falha entre 69 porque outra jornada ainda exigia a ordem DOM anterior. Atualizei essa expectativa para a ordem deliberada e acrescentei Tab pelos seis atalhos nomeados antes do filtro Loja. Não removi testes nem reduzi contagens, timeouts, retries, asserts de consulta/escopo ou recuperação.

O [artefato verification-evidence](https://github.com/arthurjoanes/loja-assistente/actions/runs/35747541226/artifacts/10703737289) inclui `frontend/test-results/results.json`, a história operacional e capturas. O [recibo](evidence/frontend-ci-20260922.json) vincula SHA/run/artefato e a [tela inicial](screenshots/publication-20260922/inicio.png), copiada sem alteração. Arquivos de capturas históricas já versionados também integram o pacote e não devem ser contados como produção nova. Os testes de geometria usam sete viewports, incluindo 320×256 CSS px; isso não mede zoom nativo.

Algumas capturas `fullPage` de resultado mostram o link “Ir para o conteúdo” sobre o documento. A análise das fontes aponta como explicação a captura além do viewport após rolagem: o link não focado fica em `position: fixed; top: -100px`, enquanto Playwright captura o documento inteiro sem voltar ao topo. Não houve registro de `activeElement` no instante dessas capturas aprovadas; portanto essa explicação é uma inferência, não uma comprovação de foco. O único trace da rodada anterior pertence à falha inicial móvel. A tela inicial publicada usa captura do viewport no início da página; nenhuma imagem teve pixels editados e o CSS do link foi preservado.

O bloqueio local anterior de inicialização continua registrado e não foi contornado. O CI remoto é uma execução distinta no SHA acima; não valida automaticamente um commit posterior de documentação. Comparação pareada com baseline, zoom nativo, leitor de tela, acessibilidade integral e desempenho percebido continuam fora dessa prova.

## Revisão autoral de portfólio — 22/09/2026

Revisei problema, conta manual, decisões, código e as três capturas reais de `f98ee948…`. A fixture `manual-v1` de R$ 30 permanece separada do caso visual `synthetic-v1` de R$ 10.810,95. O README identifica minhas contribuições e as bibliotecas que integrei; a arquitetura, o orçamento e os contratos não foram alterados.

Construí somente o backend atual, com Dockerfile e locks presentes, em tag própria: **Python 3.12.14**, imagem `sha256:54aa5ebe173e51bb354be5e4ee359fc4e7154040e80f2793ece2d7c0d5881b3e`. `scripts/check.py` passou Ruff, formato (58 arquivos), mypy (36 fontes), migrações até 0003, **364 testes** em 72,01 s e **57/57 casos offline**. Os 364 incluem os 353 da prova anterior e 11 casos de integridade histórica. Um aviso de depreciação do alias AnyIO usado pelo TestClient do Starlette permaneceu visível. O banco era temporário, sem portas; a rede era interna, LLM estava desligado e a chave vazia. Fontes foram montadas somente para leitura, com saída de relatório separada. Esses tempos, com outras tarefas no host, não são benchmark.

Preservei duas falhas de preparação: primeiro o Docker não pôde criar o ponto de montagem do relatório sob a raiz somente para leitura; depois, um endpoint fictício HTTP foi corretamente recusado pela validação de configuração antes de migrar. Criei o diretório vazio de destino e usei a URL de configuração aceita, mantendo chave vazia, modo Demo e rede sem saída. Não alterei código, testes, limiares ou guardas para obter aprovação. A terceira tentativa passou e os recursos próprios foram encerrados, sem apagar volumes alheios.

No host Windows, com Node 24.19.0 e npm 11.17.0, instalei o frontend do lock em diretório novo com `npm ci --no-audit --fund=false`. ESLint, Prettier, build de produção, TypeScript e **39 testes puros** (`domain.spec.ts`/`proxy-streams.spec.ts`, 1,3 s, sem skip/retry) passaram. Esses casos usam o runner Playwright sem abrir navegador nem iniciar servidor. O arquivo de tipos gerado pelo build foi devolvido aos bytes do snapshot, sem mudar fontes de frontend. `npm audit --package-lock-only --json` retornou zero achados em 22/09/2026; isso não cobre o sistema operacional, segredos ou a aplicação.

Gitleaks 8.30.1, com redação integral e a configuração existente, retornou zero achados nos 396 arquivos rastreados/não ignorados do snapshot e nos sete commits alcançáveis (`--all`). A invocação inicial com caminho absoluto não aplicava as exceções existentes por caminho e marcou digests/ID de correlação históricos; conservei a tentativa e corrigi a invocação para caminho relativo, sem acrescentar exceções. Não fiz nova chamada paga ou avaliação de linguagem.

Trivy 0.74.0 retornou **zero vulnerabilidades** na imagem de backend atual, via Docker local, sem filtro de severidade ou exceções. A base de avisos foi atualizada em 22/09/2026 às 07:24 UTC. O scanner manteve avisos sobre Alpine 3.24 fora de sua lista de EOL e termos adicionais em metadados de licença. Esse resultado cobre os pacotes de sistema/Python detectados, não o frontend ou uma implantação.

`python scripts/verify_evidence.py` passou sem escrita ou rede: 65 artefatos, 62 fontes históricas, dois conjuntos de casos, contagens e somas. O verificador identifica as nove fontes alteradas e os 11 módulos posteriores; não transfere 47/48 da avaliação paga para o código atual. Os resultados originais e a falha `final-bf-04` permanecem preservados. O [recibo desta revisão](evidence/portfolio-review-20260922.json) separa instalação, testes, scans e imagens históricas.

**Situação posterior: design aprovado pelo autor e 69 casos aprovados no [CI do commit `73aa1fff`](https://github.com/arthurjoanes/loja-assistente/actions/runs/35747541226), incluindo as 30 jornadas de navegador/HTTP.** A revisão autoral local descrita acima respeitou a recusa automática de inicialização, sem repetição nem método alternativo. O CI posterior produziu provas remotas distintas. A prova `f98ee948…` abaixo continua vinculada à versão congelada anterior à nova marca, fonte e composição. O procedimento local `setup/start/e2e` não foi repetido.

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

Os parágrafos desta seção registram a etapa parcial que precedeu a entrega acima. Suas pendências de navegador foram tratadas na prova posterior; foram encerradas naquela versão. A direção visual posterior foi executada no CI identificado no início deste documento, com limites em [qualidade do frontend](frontend-quality.md).

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
