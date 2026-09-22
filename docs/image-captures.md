# Capturas da interface

> Proveniência das imagens, conservando a data da execução original. Fontes: [manifesto](screenshots/current-20260922/capture.json) e [coletor](../scripts/capture_docs.cjs). Conferência documental: **22/09/2026**.

As seis capturas de `screenshots/current-20260922/` vieram do Chromium/Playwright 1.63.0 acessando a aplicação local em 22/09/2026. As telas autenticadas correspondem à fonte `6361280d`; o [registro](screenshots/current-20260922/capture.json) contém horário, viewports, respostas reais e SHA-256. Uma alteração concorrente posterior de login não faz parte desta captura: nenhuma imagem de login é apresentada. São recortes nativos de componentes e de coordenadas do navegador, sem edição de pixels: viewport desktop 1440×1000 ou móvel 390×844. O registro identifica o seletor e as dimensões; os recortes móveis têm no máximo 650 px de altura. As provas históricas completas ficam apenas em links.

| Tela atual                                                                    | O que conferir                                                                  |
| ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| [Início](screenshots/current-20260922/inicio.png)                             | Seis consultas disponíveis, em 1392×329 px                                      |
| [Início no celular](screenshots/current-20260922/inicio-mobile.png)           | As seis consultas em 370×506 px, sem corte horizontal global                    |
| [Evolução diária](screenshots/current-20260922/evolucao-diaria.png)           | Centro, 10–16/08/2026: R$ 10.810,95, 56 pedidos, 227 unidades, cobertura 7/7    |
| [Consulta com cálculo](screenshots/current-20260922/consulta-com-calculo.png) | Fórmula, fim exclusivo, fonte e as sete linhas que somam o total                |
| [Consulta no celular](screenshots/current-20260922/consulta-mobile.png)       | Somente os quatro indicadores, em 346×273 px; o gráfico fica no recorte desktop |
| [Filtro não suportado](screenshots/current-20260922/filtro-nao-suportado.png) | Pergunta por dinheiro pede esclarecimento; nenhum total geral é inventado       |

As telas foram inspecionadas visualmente. A automação conferiu HTTP 200, modo `demo`, escopo `a001`, sete linhas e soma em centavos igual ao total, cálculo disponível, recusa com resultado nulo, ausência de erro JavaScript e overflow nas seis vistas. O coletor seleciona Demo antes de enviar e bloqueia qualquer consulta com outro modo. Nenhuma chamada Azure/LLM foi feita. As consultas sintéticas permanecem no histórico da conta; não houve reset. O caso não substitui suíte completa, avaliação de linguagem, comparação pixel a pixel, zoom nativo ou auditoria integral de acessibilidade.

## Reproduzir

Com o setup iniciado, na raiz, PowerShell 7:

```powershell
docker build --file frontend/Dockerfile.e2e --tag loja-docs-capture:local frontend
$captureOutput = Join-Path $PWD 'artifacts/docs-capture-nova'
New-Item -ItemType Directory -Path $captureOutput
docker run --rm --network container:pf-loja-assistente-frontend-1 `
  --mount "type=bind,source=$PWD,target=/repo,readonly" `
  --mount "type=bind,source=$captureOutput,target=/capture" `
  --env NODE_PATH=/app/node_modules --env DOCS_SCREENSHOT_DIR=/capture `
  --env "SOURCE_COMMIT=$(git rev-parse HEAD)" `
  --entrypoint node loja-docs-capture:local /repo/scripts/capture_docs.cjs
```

O [coletor](../scripts/capture_docs.cjs) exige pasta vazia, usa gerente Aurora/Centro e base `synthetic-v1`, referência 17/08/2026. Esta rodada reutilizou a imagem de navegador `gestao-recebiveis-e2e:local`, com a mesma versão Playwright; a aplicação capturada foi a Loja em 3102. O histórico existente foi preservado. Datas reais, request IDs e quantidade de conversas podem variar; não altere PNGs para esconder essas diferenças.

## Arquivo histórico e propostas

- Os 15 PNGs diretamente em `screenshots/` mostram a interface lateral verde de 21/09/2026: seis telas de jornada, sete vistas `quality-*` e duas `welcome-*`. Conservam as provas de [verificação histórica](verification.md#arquivo-histórico-da-interface-anterior--21092026), [revisão anterior](quality-review.md) e [parser](evidence/problem-review/README.md). Não representam o produto atual.
- Os seis PNGs dos dois diretórios `screenshots/operational-proof-20260922/` têm hashes e fontes em manifestos. A [história operacional](operational-story.md) apresenta essas execuções anteriores, com barra azul e preparação lateral.
- A [tela inicial do CI](screenshots/publication-20260922/inicio.png) conserva o [recibo histórico](evidence/frontend-ci-20260922.json). Tem a direção visual atual, mas é o recorte 1280×720 daquela execução.
- Os quatro PNGs em `design/` são propostas e espécimes, explicitamente identificados na [decisão visual](frontend-quality.md); não são captura da aplicação.

A revisão inventariou os 26 PNGs anteriores, referências e hashes, sem duplicatas binárias internas. Todos têm função documental; nenhuma prova foi excluída. Cópias de fontes do experimento Azure, freeze e fingerprints preservam a reprodução da avaliação, e os snapshots antes/depois iguais comprovam que o refresh não alterou os dados; não são arquivos descartáveis.
