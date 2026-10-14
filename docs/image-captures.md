# Capturas da interface

As capturas da rodada de [12/10/2026](uiux-20261012.md) têm comparação pareada em `screenshots/uiux-20261012/`, com a aplicação real em Demo. O recibo em `evidence/uiux-20261012/` registra hashes, origem, jornadas, geometria e scanner; as capturas de setembro abaixo conservam seu contexto histórico. Elas documentam aquelas fontes; alterações posteriores precisam de uma nova captura para comprovar sua aparência.

| Estado | Antes | Depois |
| --- | --- | --- |
| Início em 320 px | [Antes](screenshots/uiux-20261012/before-chromium-inicio-320.png) | [Depois](screenshots/uiux-20261012/after-chromium-inicio-320.png) |
| Escolha do período em 390 px | [Antes](screenshots/uiux-20261012/before-chromium-pendente-390.png) | [Depois](screenshots/uiux-20261012/after-chromium-pendente-390.png) |
| Editor recolhido em 390 px | [Antes](screenshots/uiux-20261012/before-chromium-pending-collapsed-390.png) | [Depois](screenshots/uiux-20261012/after-chromium-pending-collapsed-390.png) |
| Resultado em 1440 px | [Antes](screenshots/uiux-20261012/before-chromium-resultado-1440.png) | [Depois](screenshots/uiux-20261012/after-chromium-resultado-1440.png) |
| Favoritos em 768 px | [Antes](screenshots/uiux-20261012/before-chromium-favorito-768.png) | [Depois](screenshots/uiux-20261012/after-chromium-favorito-768.png) |
| Ausência em 1024 px | [Antes](screenshots/uiux-20261012/before-chromium-sem-dados-1024.png) | [Depois](screenshots/uiux-20261012/after-chromium-sem-dados-1024.png) |

## Capturas de 22/09/2026

As seis capturas de `screenshots/current-20260922/` vieram do Chromium/Playwright 1.63.0 acessando a aplicação local em 22/09/2026. As telas autenticadas correspondem à fonte `6361280d`; o [registro](screenshots/current-20260922/capture.json) contém horário, viewports, respostas reais e SHA-256. Uma alteração concorrente posterior de login não faz parte desta captura: nenhuma imagem de login é apresentada. São recortes nativos de componentes e de coordenadas do navegador, sem edição de pixels: viewport desktop 1440×1000 ou móvel 390×844. O registro identifica o seletor e as dimensões; os recortes móveis têm no máximo 650 px de altura. As provas históricas completas ficam apenas em links.

| Tela histórica                                                                    | O que conferir                                                                  |
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
- A [tela inicial do CI](screenshots/publication-20260922/inicio.png) conserva o [recibo histórico](evidence/frontend-ci-20260922.json). Tem a direção visual de setembro, no recorte 1280×720 daquela execução.
- Os quatro PNGs em `design/` são propostas e espécimes, explicitamente identificados na [decisão visual](frontend-quality.md); não são captura da aplicação.

A revisão inventariou os 26 PNGs anteriores, referências e hashes, sem duplicatas binárias internas. Todos têm função documental; nenhuma prova foi excluída. Cópias de fontes do experimento Azure, freeze e fingerprints preservam a reprodução da avaliação, e os snapshots antes/depois iguais comprovam que o refresh não alterou os dados; não são arquivos descartáveis.

## Leitura visual conferida em 13/10/2026

Os 149 PNGs versionados foram abertos: 123 da comparação UI/UX e 26 anteriores. A revisão manteve os arquivos e seus hashes. As conclusões abaixo distinguem o que aparece na imagem do que depende de testes e recibos.

| Imagem ou conjunto | O que está visível | Conclusão e limite |
| --- | --- | --- |
| Resultado de 12/10, 1440 px | Pergunta, Centro, 10–16/08, R$ 10.810,95, 56 pedidos, 227 unidades, ticket R$ 193,05 e gráfico com base zero e teto R$ 4.130,55 | Explica a análise de vendas. O cálculo fica fora deste viewport; confira a [vista com Cálculo aberto](screenshots/uiux-20261012/after-chromium-resultado-1440-focus.png). |
| Cálculo aberto, 1440 px | Fórmula, fonte fictícia, fuso, intervalo com fim exclusivo e sete linhas | As receitas somam R$ 10.810,95; os pedidos somam 56 e as unidades, 227. Nos dois dias sem pedidos, ticket aparece indisponível. A concordância da apresentação não substitui o oráculo financeiro independente. |
| Antes/depois, início em 320/390 px | O filtro de período antes cortava o texto; depois usa uma coluna e exibe a opção completa | A mudança é visível com o mesmo estado. As imagens não certificam todos os tamanhos ou dispositivos. |
| Antes/depois, editor recolhido em 390 px | Antes, a escolha pendente ficava escondida; depois, opções e confirmação permanecem acima da resposta | Mostra a correção do fluxo; o caso sem escolha mantém Confirmar desabilitado. |
| Sem dados, cinco larguras | Pergunta de 01/01/2025, aviso de ausência e acesso ao cálculo | Não apresenta receita zero como se fosse venda apurada. Capturas de foco podem estar roladas e não mostram a página inteira. |
| Favoritos, cinco larguras | Nome, recorte salvo e ações de executar/abrir registro; foco destacado | Mostra a separação das ações. A captura histórica `evolution-favorites.png` contém HTML como texto de teste escapado, conforme [verificação](verification.md#evolução-de-12102026); não é exemplo de nome comercial. |
| Capturas móveis de setembro | A vista `current-20260922/consulta-mobile.png` contém apenas quatro indicadores; as vistas verdes anteriores pertencem a outra composição | O recorte não mostra gráfico, tabela e editor juntos; não permite avaliar essa disposição no celular. |
| Propostas A/B, marcas e tipografia | Composições rotuladas como simulação e espécimes de identidade | Explicam a decisão visual; não comprovam páginas em execução. |

O conjunto comunica pergunta, autorização de recorte, resultado e conferência. A evidência visual permanece em Demo: não comprova qualidade de interpretação por LLM, isolamento entre organizações, produtividade com pessoas ou comportamento atual após as correções de 13/10.
