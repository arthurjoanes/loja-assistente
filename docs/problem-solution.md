# Problema e solução

Desenvolvi a demonstração para o gerente ou supervisor que precisa consultar vendas de suas lojas e conferir o recorte antes de decidir. É um problema plausível: não realizei entrevista, piloto ou medição de resultado comercial.

Um dashboard com filtros é a alternativa mais simples e continua sendo a referência de correção. A hipótese de valor do assistente é reduzir a tradução manual de perguntas variadas em filtros, preservando limites, autorização e cálculo. Se a interpretação exigir decorar frases, perder qualificadores ou recusar perguntas válidas, essa vantagem não está demonstrada. Acrescentar um modelo sem medir esses erros tampouco resolve o problema.

O núcleo existente é útil: sessão → interpretação → plano estrito → autorização atual → SQL parametrizado → centavos/Decimal → resultado e cálculo únicos. A dificuldade está nas fronteiras entre intenção, capacidade, escopo, datas, qualidade dos dados e falha de provedor. O modelo nunca calcula o faturamento nem escolhe a identidade confiável.

A entrega também trata uma falha operacional distinta: perder a resposta do provedor não significa que a chamada deixou de consumir recursos. O [orçamento persistente](provider-budget.md) reserva antes do despacho e conserva uso incerto, mesmo se a resposta HTTP não puder ser gravada. A [jornada visual](operational-story.md) e os testes de orçamento têm provas separadas; uma tela correta em modo Demo não demonstra controle de cobrança externa.

## Uma conta pequena que pode ser refeita

Na fixture de testes `manual-v1`, “Quanto vendi ontem?” usa a referência de 17/08/2026, portanto consulta 16/08 na loja Centro A (`a001`). Dois pedidos concluídos entram na conta:

| Pedido | Itens e desconto total por item                        |   Receita | Unidades |
| ------ | ------------------------------------------------------ | --------: | -------: |
| `oa3`  | 2 garrafas × R$ 6 − R$ 2 de desconto; 5 ecobags × R$ 2 |     R$ 20 |        7 |
| `oa4`  | 1 caneca × R$ 10                                       |     R$ 10 |        1 |
| Total  | 2 pedidos distintos                                    | **R$ 30** |    **8** |

O ticket é R$ 30 / 2 = R$ 15. `oa5`, de R$ 100, está cancelado e não entra. O gerente B tem outro total, R$ 33, apesar de identificadores externos coincidirem. Usei esses números literais no [oráculo manual](manual-fixture.md) e em `test_independent_financial_oracle_with_multi_item_orders` e `test_same_external_identifiers_do_not_join_tenants`, em [test_analytics.py](../backend/tests/test_analytics.py). O esperado não é recalculado pela função sob teste.

Implementei o caminho pergunta → plano validado → autorização → consulta predefinida → resultado único. As [consultas](../backend/src/loja_assistente/analytics/queries.py) somam quantidade × preço − desconto, contam pedidos distintos e limitam tenant/loja/data. Valores monetários saem como strings exatas; texto, gráfico e tabela não fazem uma segunda conta financeira. Um relatório SQL com filtros seria suficiente para essas métricas; a interpretação em português acrescenta conveniência a avaliar, custo e possibilidade de recusa indevida.

Dois limites mudam o significado da resposta. Um dia coberto sem pedidos tem receita zero e ticket indisponível; um dia não carregado tem `value=null`, não zero. Os testes `test_daily_zero_is_only_emitted_for_covered_day`, `test_absence_is_not_financial_zero` e `test_partial_coverage_excludes_unloaded_sales_and_comparison` conferem essas diferenças. Pedir “somente em dinheiro” exige esclarecimento: não adicionei forma de pagamento ao plano e não descarto o qualificador silenciosamente. [Guardas e autorização](../backend/tests/test_security.py).

A [história visual](operational-story.md) mostra os três estados — consulta, recusa e nova tentativa válida — em uma versão histórica da aplicação e **outra base**, `synthetic-v1`, total R$ 10.810,95. Ela não é uma imagem da conta manual de R$ 30 nem comprova a composição local posterior.

## Conferir o resultado sem perder o recorte

Uma conversa pode misturar receita de ontem, evolução de sete dias e uma tentativa recusada. Empilhar todas as respostas e repetir uma coluna de acesso reduz o espaço disponível para conferir a tabela e dificulta localizar a pergunta desejada. A interface revisada mostra um resultado selecionado por vez e reúne o acesso em um bloco recolhível. O histórico continua disponível; selecionar outra resposta não chama o modelo nem recalcula seus indicadores.

Um exemplo reproduzível: pergunte **Quanto vendi ontem?** e depois **Mostre a evolução diária da receita nos últimos 7 dias**. Com a referência demo de 17/08/2026, a primeira usa 16/08 e a segunda usa 10–16/08. Selecione a primeira novamente e confira o período impresso nela. A seleção é de leitura: **E nos sete dias anteriores?** continua o último plano válido, portanto usa 03–09/08 neste exemplo. O aviso da interface explica essa distinção; a [regressão de seleção](../frontend/e2e/result-selection.spec.ts) compara o período recebido do servidor e observa se houve nova requisição.

Os filtros descrevem a próxima consulta; o resultado mostra as lojas e datas efetivamente usadas. **Gráfico** e **Tabela** leem o mesmo objeto, e **Cálculo** recupera a evidência daquela resposta. Para conferir casos diferentes, use **Receita em 2026-08-11** (dia coberto sem vendas), **Receita de 2026-05-18 a 2026-05-20** (cobertura parcial) e **Receita em 2026-09-01** (sem dados carregados). As [jornadas de qualidade](../frontend/e2e/quality.spec.ts) e [de consulta](../frontend/e2e/journeys.spec.ts) verificam os estados e os números; o [registro de validação](verification.md) informa quais execuções foram concluídas.

Essa organização facilita a conferência prevista pelo produto, mas não demonstra ganho de produtividade. Não houve teste com usuários; a hipótese comercial continua separada da correção técnica e da avaliação de linguagem abaixo.

## Diagnóstico histórico e contrato de sucesso

A matriz abaixo registra o estado **anterior à avaliação Azure de 21/09/2026**. Conservei o diagnóstico para tornar as mudanças e a falha final rastreáveis; ele não é a lista atual de resultados.

| Alegação / estado inicial                     | Cenário                                           | Implementação / teste existente                              | Lacuna                                                         | Correção e critério                                                                                                                                       |
| --------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------ | -------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Português natural: não demonstrada            | Pronome, cortesia, erro de digitação, continuação | Demo v3 usa regex/vocabulário; SDK somente simulado          | “Quanto eu vendi ontem?” é rejeitado; nenhum benchmark live    | Adaptar endpoint Azure v1; avaliação congelada compara campos semânticos e resultado financeiro, com recusas no denominador                               |
| Não inventar filtros: parcial                 | Pagamento, produto, horário; cortesia “só queria” | Guarda anterior ao provedor e testes de SQL ausente          | Guarda lexical também rejeita saudações/cortesia válidas       | Tornar guardas explícitas conservadoras sem remover proteção; modelo deve esclarecer todo filtro não representável; aceitação indevida bloqueia aprovação |
| Cálculo exato: testado antes                  | Itens, cancelamento, UTC/local, zero/ausência     | Fixture manual independente e PostgreSQL; centavos em string | Reexecutar no código revisado                                  | Resultado, cálculo persistido e consulta estruturada iguais; divergência financeira bloqueia aprovação                                                    |
| Autorização fora do prompt: testada antes     | Plano válido malicioso, histórico revogado        | Sessão, referências resolvidas, revalidação, listener SQL    | Reexecutar e incluir identidade no conjunto live               | Nenhum dado/SQL proibido; qualquer violação bloqueia aprovação                                                                                            |
| Provedor real confiável: não demonstrada      | Recusa, timeout, schema, quota, custo             | Responses parse, zero retry, sem fallback                    | Sem endpoint Azure; tokens, IDs e número de chamadas limitados | SDK único configurável, telemetria sanitizada e avaliação com orçamento reservado antes de cada chamada                                                   |
| Utilidade superior a filtros: não demonstrada | Mesma tarefa por pessoa do público-alvo           | Consulta estruturada já existe                               | Nenhuma pessoa avaliada                                        | Comparação técnica com filtros agora; roteiro de usuário registrado, sem alegar ganho humano                                                              |

Os resultados antigos ficam como histórico. A avaliação é registrada com horário real, hashes, ambiente, entradas/esperado/observado e falhas preservadas. Testes simulados e parser offline não são rotulados como integração live.

## Experimento definido antes

12 casos de desenvolvimento, 24 finais escritos antes do freeze e só executados depois, duas repetições finais e um smoke: até 61 chamadas, uma execução autorizada. Sem modelo juiz. Uma falha final não autoriza ajustar limiares ou buscar outra amostra até passar; corrigir exige nova avaliação documentada e autorizada.

Critérios por execução: 0 vazamentos/consultas não autorizadas; 0 divergências financeiras; 0 aceitação de qualificadores não representados; pelo menos 90% de acerto semântico total e 80% por categoria final; no máximo 10% de esclarecimentos indevidos nas perguntas executáveis. Mostrar taxa ponta a ponta, falhas de infraestrutura, p50/p95 de latência (amostra pequena), chamadas/tokens medidos e estimativa de custo separada de cobrança. Todo caso e repetição entra no denominador. Campos sem efeito (ordem das lojas, limite fora de ranking, texto da mensagem) não alteram equivalência; métrica, lojas resolvidas, datas, intenção e comparação alteram.

Valores esperados manual-v1: gerente A em 16/08 = 3.000 centavos, 2 pedidos, 8 unidades; gerente B = 3.300 centavos. Consulta estruturada é baseline de correção, não mede produtividade. Avaliação HTTP usa aplicação real/autorizações/PostgreSQL isolado; jornadas pelo proxy e navegador são testes separados.

## Resultado local

As paráfrases conhecidas deixaram de gerar esclarecimento indevido; qualificadores ausentes continuam recusados. O [comparador offline](../evals/reports/20260921T063624Z-d4d4fcdb/summary.md) passou 12/12 casos por parser e 9/9 por consulta estruturada. Os nove valores financeiros são conferidos contra a fixture manual; o esperado não é calculado pelo mesmo código da aplicação. É uma regressão local, não um teste de linguagem aberta ou de vantagem de uso.

305 testes backend e 47 casos Playwright passaram. A integração simulada do SDK cobre o caminho do plano até autorização, cálculo e persistência, incluindo rejeição de escopo alheio antes de SQL. Três riscos de aprovação/consumo foram corrigidos no avaliador: smoke confundido com aprovação final, orçamento renovado por cópia de arquivo e uso parcial tratado como custo conhecido. A recuperação do ledger e os preços capturados também têm regressões. [Logs e tentativas](evidence/problem-review/README.md).

## Limites

Recurso Azure próprio, deployment Luna conferido e teto de US$ 15. A avaliação live passou nos critérios definidos antes; resultado e limitação estão na seção seguinte. Produção, SLA e utilidade com usuários não foram testados.

## Resultado posterior à autorização Azure

A matriz acima foi registrada antes da implementação e preserva o diagnóstico original. A [avaliação real](azure-live-results.md) mostrou 47/48 resultados corretos com Luna, ante 24/48 do parser e 30/30 consultas estruturadas aplicáveis. Seis decisões de guardas locais permanecem no denominador do caminho modelo + backend, separadas das 42 chamadas finais. Houve um esclarecimento desnecessário e nenhuma falha crítica; todos os limiares definidos antes passaram. Smoke/desenvolvimento/final geraram 55 chamadas, 48.788 tokens e estimativa conservadora US$ 0,01550395. Acesso e orçamento foram fornecidos; produção e utilidade com usuários continuam não avaliados.

## Código e evidências relacionados

[fixture](../backend/tests/manual_fixture.py) · [casos](../evals/cases/manual-v1.json) · [resumo final](../evals/reports/20260921T121255Z-a9c11d1f/summary.json).
