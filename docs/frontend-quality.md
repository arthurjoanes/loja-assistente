# Qualidade da experiência analítica

**Atualização posterior:** a candidata descrita aqui foi exercitada pela rodada `f98ee94864384422bd835bcabd8f3a11`: build/checks e 68 casos aprovados, incluindo 30 jornadas de navegador/HTTP; três capturas reais em 1440×1000. [Resultado e limites](verification.md#validação-final-da-candidata-de-interface) · [sequência capturada](operational-story.md). Dos 45 hashes desta candidata, 44 ficaram iguais; somente o coletor recebeu conclusão de transições e metadados. A matriz e os relatos abaixo preservam o estado da revisão estática original. A nova rodada não executou todo o estudo visual comparativo proposto nem participantes/leitor de tela.

Revisão de 22/09/2026 sobre o **estado local da interface já reconstruída**, incluindo seleção de resultados e `daily-series.ts`, ainda não publicado. O HEAD era `849428f4c1fd6b166516553f43c5466d8fee6de0`, mas o baseline inclui alterações locais posteriores. Comparar apenas com esse commit perderia trabalho válido. Uma conferência final identificou mudanças concorrentes de contraste, foco, jornadas e documentação de orçamento; elas foram preservadas e os refinamentos reaplicados ao estado atualizado antes de repetir os checks. O [registro estático](evidence/frontend-quality-static-20260922.json) distingue baseline inicial, baseline de integração e candidato.

**Validação parcial:** lint, tipos, build e testes puros foram conferidos. Nenhum servidor, navegador, nova captura ou chamada paga foi iniciado nesta revisão. A inicialização do frontend já tinha sido rejeitada pela revisão automática (`blocked by policy`); não houve repetição ou alternativa. As 30 jornadas de navegador/HTTP e a revisão visual deste candidato continuam pendentes. Este documento não aprova publicação.

Em paralelo, a rodada `96ae56f146d044d8ada235c3dbfc1c0c` aprovou 68 verificações e gerou capturas da fonte anterior a estes incrementos, conforme o [índice da entrega](evidence/operational-proof-20260922/index.json) e a [história verificada](operational-story.md). Suas correções de contraste e foco foram incorporadas ao baseline de integração. Essa prova permanece com seu escopo; não é uma execução deste candidato.

## Inventário de decisões, telas e estados

Gerentes consultam suas lojas; supervisores combinam lojas autorizadas. A decisão é entender o resultado de uma pergunta comercial e conferir se período, lojas e cobertura sustentam sua leitura. A IA interpreta; o servidor autoriza e calcula. [Problema e exemplos](problem-solution.md), [guia da interface](interface.md) e [métricas](metrics.md) detalham essas regras.

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

## Referências e composição preservada

O [Explore do Superset](https://superset.apache.org/user-docs/using-superset/creating-your-first-dashboard/#creating-charts-in-explore-view) separa configuração, execução e leitura de gráfico/dados. O [Explorer público do Lightdash](https://demo.lightdash.com/projects/thyme-to-shine-market/saved/what-are-the-weekly-revenue-stats-) e sua [documentação](https://docs.lightdash.com/introduction) orientaram a relação entre pergunta, gráfico, tabela e métrica. A pesquisa anterior distinguiu produto real Lightdash de imagem oficial de documentação Superset; não era estudo de usabilidade da Loja. Nesta rodada foram relidas as fontes, sem copiar código, marca ou assets.

O baseline local já prioriza um resultado por vez, pergunta como título, recorte aplicado e cobertura à frente, formulário à esquerda no desktop e recolhido até 1024 px. A série diária ocupa a largura disponível, sem mínimo de 3300 px para 30 dias nem destaque arbitrário do primeiro dia. Tabela exata e cálculo permanecem acessíveis. Essas decisões foram preservadas, pois atendem ao trabalho analítico. Não foi imposta a composição de outro projeto.

Não adotamos catálogo editável, SQL livre, salvar dashboard, metas, previsão ou filtros fora do contrato. Dinheiro não é arredondado para K/M para caber. Ausência de overflow não comprova legibilidade. As [Web Interface Guidelines](https://github.com/vercel-labs/web-interface-guidelines/blob/main/command.md), relidas em 22/09/2026, e os critérios de [reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html) e [contraste não textual](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html) orientam a revisão; não certificam este frontend.

## Achados e intervenção

| Evidência estática | Impacto / prioridade | Alteração | Validação / limite |
|---|---|---|---|
| `globals.css`: snapshot inicial com etapas de login em `#c4bece` sobre fundo claro; rótulo/descrição inline | Contraste insuficiente e leitura sem separação; P1 | Correção concorrente para `--muted` preservada; acrescentados rótulo 14 px/descrição 13 px e blocos separados | Par calculado; composição real não verificada |
| `visualization.tsx`: cabeçalhos de métricas à esquerda, valores à direita | Associação entre coluna e número; P2 | Cabeçalho e valor numéricos à direita | Diff, tipos/build; tabela real pendente |
| `operations.tsx`: durações à esquerda; “uso e custo não medidos” | Alinhamento inconsistente e afirmação ampla sobre todo o sistema; P2 | Durações à direita; “Não expostos neste painel” | Preserva payload e orçamento; não inventa custo |
| `analysis-sidebar.tsx`: área atual apenas por classe CSS | Estado não comunicado semanticamente; P2 | `aria-current="page"` nos destinos | Inspeção; leitor de tela/foco pendentes |
| `question-composer.tsx`: Enter envia durante composição IME | Confirmar caractere pode enviar pergunta antes de terminá-la; P1 | Não aplica atalho enquanto `nativeEvent.isComposing`; Enter normal/Shift+Enter preservados | Regressão no caso de campos existente, não executada |
| Bordas claras, foco comum sobre navy e drawer sem contenção | Contorno/foco pouco perceptíveis e rolagem do fundo; P2 | Borda `#7a899e`, foco claro no cabeçalho, `overscroll-behavior: contain` | Pares calculados; dispositivo não verificado |
| `quality-review.md` não separava capturas antigas da reconstrução | Atribuição incorreta de prova; P1 documental | Referência à matriz e rótulo histórico explícito | Links e coerência documental |

Nenhum P0 foi identificado na inspeção. Isso não elimina a execução das jornadas de cálculo, acesso, foco e falhas antes de publicar.

## Matriz das 11 dimensões

Antes = snapshot local já reconstruído; depois = este refinamento. C = Conforme no escopo estático/documental; P = Parcialmente conforme; NC = Não conforme; NV = Não verificado; NA = Não aplicável. **C não significa validação visual.** NV permanece onde a conclusão exige renderização/interação real.

| Dimensão | Login / sessão | Início / formulário | Agregado / comparação | Ranking / série / tabela | Cálculo | Histórico / seleção | Menu / conta | Atendimentos |
|---|---|---|---|---|---|---|---|---|
| 1. Objetivo e público | C→C | C→C | C→C | C→C | C→C | C→C | C→C | C→C |
| 2. Hierarquia da informação | P→P | P→P | P→P | P→P | P→P | P→P | P→P | P→P |
| 3. Layout, alinhamento, espaçamento, densidade | NV→NV | NV→NV | NV→NV | P→NV | NV→NV | NV→NV | NV→NV | P→NV |
| 4. Tipografia, cores e consistência | NC→P | P→P | P→P | P→P | P→P | P→P | P→P | P→P |
| 5. Indicadores, gráficos e tabelas | NA→NA | NA→NA | C→C | P→P | C→C | NA→NA | NA→NA | P→P |
| 6. Navegação, filtros, formulário e ações | NV→NV | P→NV | NV→NV | NV→NV | NV→NV | NV→NV | P→NV | NV→NV |
| 7. Loading, vazio, erro e atualização | P→P | P→P | P→P | P→P | P→P | P→P | P→P | P→P |
| 8. Acessibilidade e responsividade | NV→NV | NV→NV | NV→NV | NV→NV | NV→NV | NV→NV | NV→NV | NV→NV |
| 9. Desempenho | P→P | P→P | P→P | P→P | P→P | P→P | P→P | P→P |
| 10. Manutenção e reaproveitamento | C→C | C→C | C→C | C→C | C→C | C→C | C→C | C→C |
| 11. Dados, regras e permissões | C→C | C→C | C→C | C→C | C→C | C→C | C→C | C→C |

NA na dimensão 5: login, preparação, navegação e seletor não apresentam análise numérica própria. Cobertura parcial/ausente pertence às colunas de resultado; carregamento, erro e sessão abrangem todas as áreas. P em hierarquia/estados significa sequência e ramificações presentes no código, sem aprovação em uso. P em desempenho limita a conclusão ao build/estrutura: latência percebida e render não foram medidos.

## Grade, texto, estados e custo de execução

Preservamos área centrada até 1608 px, margens de 24 px no desktop, 16/10 px nas telas menores, consulta de 292/264 px e resultado flexível. Até 1024 px, formulário no fluxo e recolhido; até 800 px, navegação em drawer. São configurações CSS, não medidas de layout aprovado. O gráfico não compete com acesso permanentemente aberto.

A paleta existente usa navy para produto, azul para ação e estados semânticos com rótulos. Uma família local Segoe UI/Arial evita download de fontes. Valores tabulares e longos podem quebrar sem ocultar centavos. Pares de contraste alterados foram calculados isoladamente; todos os estados e alvos reais ainda precisam de inspeção.

Sem biblioteca nova, cache entre usuários, cálculo financeiro no JSX ou contrato alterado. `Number` continua restrito à geometria; dinheiro/ticket exibidos usam valores decimais recebidos. Zero, ausência, parcial, ticket indisponível e percentual sem base continuam distintos. Indicadores comparáveis permanecem visíveis; explicação, cálculo, metadados e preparação podem ser recolhidos.

Seleção antiga mantém gráfico/tabela/cálculo daquela resposta montados, sem nova consulta. Isso preserva estado e pode aumentar o DOM em conversas longas: não há benchmark de custo constante. Ranking tem até 20 linhas, período até 90 dias e Atendimentos até 100 registros. Não introduzimos virtualização sem avaliação de foco, semântica e volume. Guards de sessão, geração de consulta e respostas antigas ficaram intactos.

Transições de 140 ms são explícitas; `prefers-reduced-motion` reduz animação/rolagem. A rolagem ao resultado/erro permanece a existente. Foco de menu, formulário, seleção e cálculo tem jornadas preparadas, sem nova execução nesta revisão.

## Provas e fechamento necessário

Passaram ESLint, Prettier, TypeScript, build de produção e **38 testes puros** de domínio/transporte, sem skip/retry. A listagem atual contém 68 casos: 38 puros e 30 dependentes de navegador/HTTP. A contagem de 29 da revisão anterior não incluía `operational-story.spec.ts`, já presente no snapshot inicial desta rodada. A regressão IME amplia uma jornada existente, portanto permanecem **30 jornadas de navegador/HTTP não executadas**. Testes puros exercitam formatação, períodos, transições, série e streams simulados; não comprovam UI ou orçamento concorrente.

A [evolução anterior](screenshots/evolucao-diaria.png) foi relida para contexto: mostra conversa/painéis laterais anteriores, não este snapshot. As capturas de `operational-proof-20260922` pertencem à rodada paralela documentada acima e às fontes identificadas por ela. Esta revisão não produziu screenshots novos nem um par comparativo de baseline/candidato.

Para fechar, executar baseline/candidato com mesmo seed, conta `gerente.a@demo.local`, modo demo, referência 17/08/2026 e histórico de uma conversa. Repetir receita ontem, ranking e evolução de 1/7/30 dias com os mesmos filtros/seleção. Capturar login, início, resultado, tabela, cálculo, histórico, menu, Atendimentos e parcial/ausente/erro/loading, identificando respostas controladas. Comparar 1440×900, 1366×768, 1024×900, 768×1024, 390×844 e 320×844; verificar zoom nativo 200%, teclado, foco, não sobreposição, fim da evidência, overflow global e rolagem local. Geometria 320×256 não comprova zoom nativo 400%.

Não houve estudo com usuários, chamada Azure/OpenAI, teste de carga ou certificação AA. Backend, avaliação, orçamento, credenciais e provas concorrentes ficaram fora desta rodada. Resultados históricos de modelo continuam restritos às fontes e datas dos respectivos relatórios.
