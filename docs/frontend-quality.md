# Qualidade da experiência analítica

Direção visual de 22/09/2026 sobre o **estado local da interface já reconstruída**, incluindo alterações concorrentes de orçamento/provas e o refinamento anterior. O HEAD de partida era `849428f4c1fd6b166516553f43c5466d8fee6de0`, com fontes locais posteriores; o baseline foi registrado por conteúdo, incluindo `daily-series.ts`. A proposta põe **pergunta, recorte, resposta e conferência** à frente, com identidade própria. Não é um diff apenas contra aquele HEAD.

**Design aprovado pelo autor em 22/09/2026; validação de execução parcial:** lint, tipos, build e 39 testes puros passaram. Nenhum servidor, navegador, captura nova de aplicação ou chamada paga foi iniciado nesta rodada. A inicialização anterior havia sido rejeitada pela revisão automática (`blocked by policy`); não houve repetição nem alternativa. As **30 jornadas de navegador/HTTP deste candidato continuam não executadas**. O [manifesto desta direção](evidence/visual-direction-static-20260922.json) conserva fontes, verificações e limites da rodada técnica; a aprovação posterior do design não altera esses resultados.

As provas paralelas `96ae56f146d044d8ada235c3dbfc1c0c` e a posterior `f98ee94864384422bd835bcabd8f3a11` registram 68 verificações e capturas de fontes anteriores a esta direção visual: [índice](evidence/operational-proof-20260922/index.json), [história verificada](operational-story.md). A rodada posterior verificou o refinamento anterior em 1440×1000, com 44/45 hashes iguais e alteração apenas do coletor. Essas execuções não foram repetidas nem atribuídas à nova composição; a atualização histórica foi preservada conforme [verificação final anterior](verification.md#validação-final-da-candidata-de-interface). A [revisão estática anterior](evidence/frontend-quality-static-20260922.json) também conserva seu escopo.

## Inventário de decisões, telas e estados

Gerentes consultam suas lojas; supervisores combinam lojas autorizadas. A decisão é entender o resultado de uma pergunta comercial e conferir se período, lojas e cobertura sustentam sua leitura. No modo Demo, o parser determinístico interpreta a pergunta; quando habilitada, a IA pode fazer essa interpretação. O servidor autoriza e calcula em ambos os modos. [Problema e exemplos](problem-solution.md), [guia da interface](interface.md) e [métricas](metrics.md) detalham essas regras.

| Tela / estado | Informação e ação essenciais | Suíte prevista |
|---|---|---|
| Login, senha inválida, bootstrap, sessão expirada | Conta/organização/lojas, erro recuperável, senha sem apagar seleção | `round-2-fields`, `journeys` |
| Início e nova análise | Capacidades reais, seis consultas iniciais, Pergunta acessível, sem resultado inventado | `review`, `quality`, `result-selection` |
| Preparar consulta / período personalizado | Lojas permitidas, modo, datas reais/fim exclusivo, validação e rascunho | `round-2-fields`, `domain` |
| Agregado e comparação | Métrica pedida, totais do mesmo recorte, base/período da comparação | `journeys`, `quality` |
| Ranking e tabela | Classificação, total de todos os produtos, nomes e valores exatos | `journeys`, `quality` |
| Evolução de 1/7/30 dias | Calendário contínuo, lacuna diferente de zero, visão geral e tabela | `domain`, `quality` |
| Parcial, ausente, esclarecimento, erro do provedor | Limite junto do resultado, sem total enganoso nem fallback silencioso | `quality`, `round-2-fields`, `operational-story` |
| Cálculo aberto/fechado, carregando, erro e repetição | Fórmula, fonte, fuso, lojas, datas, cobertura, totais diários e correlação | `quality`, `round-2-fields` |
| Histórico, resultado antigo, continuação | Seleção não consulta novamente; continuação usa último plano válido | `result-selection`, `domain` |
| Menu móvel, conta e logout | Área atual, foco contido, Escape/retorno, isolamento de sessão | `journeys`, `quality` |
| Atendimentos carregando/vazio/antigo/detalhado | Amostra pessoal, estado/durações do serviço, aviso de atualização falha | `round-2-fields`, `journeys` |

Esses nomes identificam suítes, não execuções desta rodada. Apenas `domain` e os testes puros de streams foram executados; nenhuma jornada dependente de página/API foi.

## Diagnóstico e duas alternativas antes de expandir

As prioridades indicam o impacto do problema no baseline: P1 compromete a tarefa ou a compreensão do resultado; P2 representa atrito de leitura; P3 é refinamento visual. A validação abaixo aponta inspeções e testes já registrados; a validação visual/interativa em execução permanece bloqueada.

| Evidência do baseline atual | Efeito sobre a leitura | Prioridade | Intervenção | Validação e limite |
|---|---|---|---|---|
| Preparação ocupava coluna permanente à esquerda; indicadores e gráfico vinham empilhados | Espaço da pergunta competia com a resposta | P2 | Resposta usa a largura principal; totais em faixa lateral ao gráfico e preparação abaixo | Ordem do DOM e breakpoints inspecionados. Proporção, overflow e comparação com mesmo recorte/largura: não verificados |
| Início recolhia a pergunta em telas menores e oferecia “Editar” sem resposta | Primeira consulta dependia de descobrir o editor | P1 | Nova consulta aparece primeiro, expandida, antes dos seis atalhos; próxima/editar só após resposta | [Fonte da área de análise](../frontend/src/features/assistant/workspace.tsx) distingue início e resposta. Jornada móvel de primeira consulta, reabertura e foco apenas listada, não executada |
| Métricas, gráfico, cálculo e controles compartilhavam molduras | Dificuldade de distinguir leitura, confirmação e edição | P2 | Resposta branca, totais em superfície neutra, cálculo em faixa própria e preparação cinza azulada | Tokens e nove pares principais de contraste conferidos estaticamente. Hierarquia percebida e estados sobrepostos: não verificados |
| Ranking destacava o primeiro item por cor e série não mostrava teto numérico | Ênfase sem estado semântico; escala pouco explícita | P1 | Barras da mesma métrica têm a mesma cor; base/teto e datas tornam a escala explícita, com tabela exata | [Gráfico e tabela](../frontend/src/features/analytics/visualization.tsx) inspecionados; teste puro do teto decimal/zero/ausência aprovado. Série 1/7/30 dias, teclado e valores visíveis no navegador: não verificados |
| Ícone quadrado e fonte de sistema pareciam genéricos | Identidade não relacionava pergunta e cálculo | P3 | Símbolo original de delimitação/igualdade, Source Sans 3 e acento petróleo | SVGs/fontes e amostras 16/24/32 px inspecionados estaticamente. Carregamento, fallback e favicon na aplicação: não verificados |

As propostas usam **o mesmo caso já documentado**: Centro, 10–16/08/2026, demo `synthetic-v1`, receita R$ 10.810,95, 56 pedidos, 227 unidades, ticket R$ 193,05 e cobertura 7/7. A série é R$ 1.557,80; zero; zero; R$ 1.831,00; R$ 1.543,70; R$ 1.747,90; R$ 4.130,55. A fonte é a [captura histórica do cálculo](screenshots/operational-proof-20260922/96ae56f146d044d8ada235c3dbfc1c0c/01-calculation.png), não dados inventados.

- [Proposta A — consulta no topo](design/proposta-a.png) ([SVG](design/proposta-a.svg)): formulário permanente acima e cálculo lateral. Rejeitada por continuar dando protagonismo aos controles.
- [Proposta B — leitura analítica](design/proposta-b.png) ([SVG](design/proposta-b.svg)): pergunta/escopo, total ao lado da evolução, conferência abaixo e próxima consulta no fim. **Escolhida** pela relação entre pergunta e resposta e pela área útil do gráfico.

São **simulações de composição**, rotuladas na imagem; não são captura da aplicação. A proposta omite escala numérica do gráfico e não serviria como versão final: o código conserva e explicita unidade, base/teto, datas e valores em tabela. A etapa sem resposta recebe tratamento próprio: consulta visível antes dos atalhos, sem painel vazio reservado para uma resposta futura.

## Referências e tradução para o produto

O [Explorer do Lightdash](https://docs.lightdash.com/introduction) foi observado em sua [demo pública](https://demo.lightdash.com/projects/thyme-to-shine-market/saved/what-are-the-weekly-revenue-stats-); o [Explore do Superset](https://superset.apache.org/user-docs/using-superset/creating-your-first-dashboard/#creating-charts-in-explore-view), em imagem oficial de documentação. Foram reaproveitadas as relações entre métrica, gráfico, tabela e recorte. Rejeitamos catálogo de campos, SQL livre, duas colunas permanentes de edição e números abreviados. A aplicação continua oferecendo somente as capacidades autorizadas pelo servidor. Nenhum código ou asset desses produtos foi copiado; suas licenças não são uma licença geral para imagens ou dependências.

| Fonte primária / material visto em 22/09/2026 | Aproveitado e adaptado | Rejeitado / licença |
|---|---|---|
| [Linear — redesenho](https://linear.app/now/how-we-redesigned-the-linear-ui), imagem oficial da interface com lista e detalhe | Contraste entre navegação, edição e conteúdo; cor intensa tem uma função | Não copiar shell, código, marca ou imagem. A publicação não concede licença para reutilizar seus assets |
| [Carbon — tabelas](https://carbondesignsystem.com/components/data-table/usage/) e [eixos/rótulos](https://carbondesignsystem.com/data-visualization/axes-and-labels/) | Alinhamento numérico, unidade e comparabilidade; controles junto do trabalho | Não adicionar gráficos para decorar nem arredondar dinheiro para K/M; padrões consultados, nenhum componente copiado |
| [Atlassian — cor](https://atlassian.design/foundations/color/) e [Radix — escalas](https://www.radix-ui.com/colors/docs/palette-composition/understanding-the-scale) | Separar fundo, elemento interativo, texto e status | Não adotar as paletas como identidade pronta; sem pacote ou tokens copiados |
| [Pentagram — Galaxy](https://www.pentagram.com/work/galaxy), aplicação real de símbolo e wordmark | Um gesto reconhecível que funciona sem ornamento e em aplicações diferentes | Não reutilizar círculo/quadrado, desenho ou marca; direitos dos autores |
| [Swavee — identidade conceitual](https://www.behance.net/gallery/241721015/Visual-Identity-design-for-Swavee), apresentação dos designers Tobi Victor/Nifemi Adelana | Relação entre nome, símbolo e aplicação; referência fictícia explicitamente identificada | Não copiar letras, esfera, fotos, gradientes ou marketing. Portfólio conceitual não comprova usabilidade nem exclusividade |

As [Web Interface Guidelines](https://github.com/vercel-labs/web-interface-guidelines/blob/main/command.md) foram consultadas em 22/09/2026. Foram aplicados foco visível, redução de movimento, campos nomeados, consulta/aplicação separadas e ausência de dependência visual nova. [Estado em React](https://react.dev/learn/choosing-the-state-structure), [reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html) e [alvos](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html) orientam decisões; não certificam a aplicação. Estas fontes sustentam padrões e inferências de design, não uma avaliação de usabilidade com usuários.
## Identidade, tipografia e superfícies

O símbolo original combina delimitadores de consulta e igualdade: pergunta e cálculo, sem balão genérico de chat. [Wordmark](../frontend/public/brand/wordmark.svg), [compacto](../frontend/public/brand/mark.svg), [mono](../frontend/public/brand/mark-mono.svg), [reverso](../frontend/public/brand/mark-reverse.svg) e [favicon](../frontend/src/app/icon.svg) são SVG. O produto preserva nome acessível e símbolo decorativo. A [conferência em 16/24/32 px](design/marcas-16-24-32.png) mostrou os delimitadores/igualdade distinguíveis em rasterização estática; a aba real ainda não foi inspecionada. Não há alegação de exclusividade jurídica.

A [comparação de tipografia](design/tipografia.png) usou arquivos reais convertidos em contornos, não fallback de renderizador. Source Sans 3 foi escolhida para perguntas, explicações e números; IBM Plex Sans ficou na carteira financeira. O WOFF2 variável 200–900 soma **170.188 bytes**, custo novo antes de transporte/cache. `next/font/local`, `display: swap` e Arial de fallback evitam dependência de serviço remoto. Glifos PT-BR/moeda e avanços iguais dos dígitos foram conferidos por FontTools; o arquivo não tem feature `tnum`, e o CSS continua declarando números tabulares. Fonte efetivamente carregada e fallback no browser permanecem não verificados.

Arquivo Adobe no commit `87b37a2daaed80fcb8e8ccb0085c4d72ddade12e`, com [origens/hashes](../frontend/src/app/fonts/sources.json) e [OFL 1.1 integral](../frontend/src/app/fonts/source-sans-LICENSE.md), sem alteração. Fontes e código têm licenças próprias. Não foram acrescentadas dependências de UI, gráficos ou ícones.

Conteúdo centrado até 1488 px incluindo margens de 24 px; 16/10 px em telas menores. A resposta ocupa a linha; quando há visualização, os totais usam 230–280 px e o gráfico recebe o restante. Até 1024 px, os totais ficam acima e a próxima consulta pode recolher; até 800 px, navegação em drawer; até 540 px, preparação e métricas ficam em fluxo compacto. Sem resposta, a preparação permanece aberta. Login separa contexto e acesso, com uma coluna em tela estreita. Essas são regras do CSS, não medições de reflow aprovado.

Canvas `#f0f2f3`, resposta branca, totais `#eff3f4`, preparação `#e2eaec`, ação `#0c6273` e gráfico `#147b91`. Verde informa cobertura completa; âmbar informa parcial/ausência; erros têm vermelho e texto. A referência de data não usa verde como se fosse saúde do serviço. Histórico claro conserva contraste em repouso/hover/seleção. Nove pares principais passaram cálculo isolado de contraste. As transições de 140 ms e `prefers-reduced-motion` permanecem; não há entrada ornamental de cards.

## Matriz das 11 dimensões

Antes = snapshot local já reconstruído; depois = este refinamento. C = Conforme no escopo estático/documental; P = Parcialmente conforme; NC = Não conforme; NV = Não verificado; NA = Não aplicável. **C não significa validação visual.** NV permanece onde a conclusão exige renderização/interação real.

| Dimensão | Login / sessão | Início / formulário | Agregado / comparação | Ranking / série / tabela | Cálculo | Histórico / seleção | Menu / conta | Atendimentos |
|---|---|---|---|---|---|---|---|---|
| 1. Objetivo e público | C→C | C→C | C→C | C→C | C→C | C→C | C→C | C→C |
| 2. Hierarquia da informação | P→P | P→P | P→P | P→P | P→P | P→P | P→P | P→P |
| 3. Layout, alinhamento, espaçamento, densidade | NV→NV | NV→NV | NV→NV | P→NV | NV→NV | NV→NV | NV→NV | P→NV |
| 4. Tipografia, cores e consistência | P→P | P→P | P→P | P→P | P→P | P→P | P→P | P→P |
| 5. Indicadores, gráficos e tabelas | NA→NA | NA→NA | C→C | P→P | C→C | NA→NA | NA→NA | P→P |
| 6. Navegação, filtros, formulário e ações | NV→NV | P→NV | NV→NV | NV→NV | NV→NV | NV→NV | P→NV | NV→NV |
| 7. Loading, vazio, erro e atualização | P→P | P→P | P→P | P→P | P→P | P→P | P→P | P→P |
| 8. Acessibilidade e responsividade | NV→NV | NV→NV | NV→NV | NV→NV | NV→NV | NV→NV | NV→NV | NV→NV |
| 9. Desempenho | P→P | P→P | P→P | P→P | P→P | P→P | P→P | P→P |
| 10. Manutenção e reaproveitamento | C→C | C→C | C→C | C→C | C→C | C→C | C→C | C→C |
| 11. Dados, regras e permissões | C→C | C→C | C→C | C→C | C→C | C→C | C→C | C→C |

NA na dimensão 5: login, preparação, navegação e seletor não apresentam análise numérica própria. Cobertura parcial/ausente pertence às colunas de resultado; carregamento, erro e sessão abrangem todas as áreas. P em hierarquia/estados significa sequência e ramificações presentes no código, sem aprovação em uso. P em desempenho limita a conclusão ao build/estrutura: latência percebida e render não foram medidos.

## Contratos, custo e verificações

Sem alteração de backend, auth, provedor, orçamento, transporte, regras ou payloads. Recorte aplicado, cobertura, seleção/continuação e estados parcial/ausente/zero continuam distintos. O frontend não calcula receita ou ticket; o teto do gráfico **seleciona um valor já recebido** por comparação decimal exata. `Number` continua restrito à geometria. A seleção do teto cobre frações de centavo sem converter a apresentação para ponto flutuante. A tabela preserva linhas exatas e datas sem linha continuam lacunas. O ranking não colore arbitrariamente a primeira posição.

A área principal inclui leitura e consulta na ordem do DOM. Sem resposta, preparação antes dos atalhos; depois da resposta, preparação abaixo da leitura. O painel tem chave estável na reconciliação. Estados de negócio não foram movidos para CSS; query/applied permanecem distintos. Seleção antiga conserva gráfico/tabela/cálculo sem reconsulta. O DOM pode crescer em conversas longas: não há benchmark de custo constante. Ranking até 20 linhas, período até 90 dias e Atendimentos até 100 registros continuam os limites existentes; não foi introduzida virtualização sem medição.

**ESLint, Prettier, TypeScript, build de produção e 39 testes puros aprovados**, sem skip/retry. São os 38 anteriores mais uma regressão de teto decimal exato/zero/ausência. A listagem contém 69 casos: 39 puros e 30 de navegador/HTTP não executados. A jornada móvel existente foi atualizada para primeira consulta visível, ordem/foco, resposta e reabertura/recolhimento; só foi listada, não executada. Build e teste puro não comprovam UI, orçamento ou chamadas IA. Nenhum recurso de aplicação foi criado.

As capturas de `operational-proof-20260922` permanecem históricas em relação a este candidato. Para fechar: baseline/candidato com mesmo seed, conta `gerente.a@demo.local`, modo demo, referência 17/08/2026, pergunta, recorte, cobertura e seleção. Comparar login, primeira consulta, agregado, ranking, série 1/7/30 dias, tabela, cálculo, histórico, menu, Atendimentos e erro/loading/parcial/ausente em 1440×900, 1366×768, 1024×900, 768×1024, 390×844 e 320×844; zoom nativo 200%, teclado/foco, overflow, fim da evidência e movimento reduzido. **Renderização, jornadas e desempenho percebido continuam Não verificados.** Sem estudo com usuários, chamada paga ou certificação AA nesta rodada. A aprovação do design não comprova as jornadas pendentes.
