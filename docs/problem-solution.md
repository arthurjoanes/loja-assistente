# Problema, solução e prova

Revisão iniciada em 21/09/2026. Público: gerente ou supervisor que precisa consultar vendas de suas lojas e conferir o recorte antes de tomar uma decisão. Problema plausível, sem entrevista, piloto ou resultado comercial observado.

Um dashboard com filtros é a alternativa mais simples e continua sendo a referência de correção. A hipótese de valor do assistente é reduzir a tradução manual de perguntas variadas em filtros, preservando limites, autorização e cálculo. Se a interpretação exigir decorar frases, perder qualificadores ou recusar perguntas válidas, essa vantagem não está demonstrada. Acrescentar um modelo sem medir esses erros tampouco resolve o problema.

O núcleo existente é útil: sessão → interpretação → plano estrito → autorização atual → SQL parametrizado → centavos/Decimal → resultado e evidência únicos. A dificuldade está nas fronteiras entre intenção, capacidade, escopo, datas, qualidade dos dados e falha de provedor. O modelo nunca calcula o faturamento nem escolhe a identidade confiável.

## Diagnóstico e contrato de sucesso

| Alegação / estado inicial | Cenário | Implementação / evidência existente | Lacuna | Correção e critério |
|---|---|---|---|---|
| Português natural: não demonstrada | Pronome, cortesia, erro de digitação, continuação | Demo v3 usa regex/vocabulário; SDK somente simulado | “Quanto eu vendi ontem?” é rejeitado; nenhum benchmark live | Adaptar endpoint Azure v1; avaliação congelada compara campos semânticos e resultado financeiro, com recusas no denominador |
| Não inventar filtros: parcial | Pagamento, produto, horário; cortesia “só queria” | Guarda anterior ao provedor e testes de SQL ausente | Guarda lexical também rejeita saudações/cortesia válidas | Tornar guardas explícitas conservadoras sem remover proteção; modelo deve esclarecer todo filtro não representável; aceitação indevida bloqueia aprovação |
| Cálculo exato: evidência anterior | Itens, cancelamento, UTC/local, zero/ausência | Fixture manual independente e PostgreSQL; centavos em string | Reexecutar no código revisado | Resultado, evidência e consulta estruturada iguais; divergência financeira bloqueia aprovação |
| Autorização fora do prompt: evidência anterior | Plano válido malicioso, histórico revogado | Sessão, referências resolvidas, revalidação, listener SQL | Reexecutar e incluir identidade no conjunto live | Nenhum dado/SQL proibido; qualquer violação bloqueia aprovação |
| Provedor real confiável: não demonstrada | Recusa, timeout, schema, quota, custo | Responses parse, zero retry, sem fallback | Sem endpoint Azure, tokens/IDs/rodada limitada | SDK único configurável, telemetria sanitizada e avaliação com orçamento reservado antes de cada chamada |
| Utilidade superior a filtros: não demonstrada | Mesma tarefa por pessoa do público-alvo | Consulta estruturada já existe | Nenhuma pessoa avaliada | Comparação técnica com filtros agora; roteiro de usuário registrado, sem alegar ganho humano |

Os resultados antigos permanecem históricos. A rodada desta revisão será registrada com horário real, hashes, ambiente, entradas/esperado/observado e falhas preservadas. Testes simulados e parser offline não serão rotulados como integração live.

## Experimento previamente definido

12 casos de desenvolvimento, 24 finais preparados por revisor independente, duas repetições finais e um smoke: até 61 chamadas, uma rodada autorizada. Casos finais ficam ocultos do implementador até congelar código/prompt/schema. Sem modelo juiz. Uma falha final não autoriza ajustar limiares ou buscar outra amostra até passar; corrigir exigirá nova rodada explicitamente documentada/autorizada.

Critérios por execução: 0 vazamentos/consultas não autorizadas; 0 divergências financeiras; 0 aceitação de qualificadores não representados; pelo menos 90% de acerto semântico total e 80% por categoria final; no máximo 10% de esclarecimentos indevidos nas perguntas executáveis. Mostrar taxa ponta a ponta, falhas de infraestrutura, p50/p95 de latência (amostra pequena), chamadas/tokens medidos e estimativa de custo separada de cobrança. Todo caso e repetição entra no denominador. Campos sem efeito (ordem das lojas, limite fora de ranking, texto da mensagem) não alteram equivalência; métrica, lojas resolvidas, datas, intenção e comparação alteram.

Oráculo manual-v1: gerente A em 16/08 = 3.000 centavos, 2 pedidos, 8 unidades; gerente B = 3.300 centavos. Consulta estruturada é baseline de correção, não prova de produtividade. Avaliação HTTP usa aplicação real/autorizações/PostgreSQL isolado; jornadas pelo proxy e navegador permanecem provas separadas.

## Resultado local da revisão

As paráfrases conhecidas deixaram de gerar esclarecimento indevido; qualificadores ausentes continuam recusados. O [comparador offline](../evals/reports/20260921T063624Z-d4d4fcdb/summary.md) passou 12/12 casos por parser e 9/9 por consulta estruturada. Os nove valores financeiros são conferidos contra a fixture manual; o esperado não é calculado pelo mesmo código da aplicação. Essa é uma prova de regressão local, não de linguagem aberta ou de vantagem de uso.

305 testes backend e 47 casos Playwright passaram. A integração simulada do SDK comprova o caminho do plano até autorização, cálculo e evidência, incluindo rejeição de escopo alheio antes de SQL. Revisão independente do avaliador corrigiu três riscos de aprovação/consumo: smoke confundido com aprovação final, orçamento renovado por cópia de arquivo e uso parcial tratado como custo conhecido. A recuperação do ledger e os preços capturados também têm regressões. [Evidências e tentativas](evidence/problem-review/README.md).

## Limites

A dependência registrada na preparação foi resolvida: recurso Azure fornecido pelo usuário, deployment Luna conferido e teto de US$ 15 autorizado. A rodada live passou nos critérios prévios; resultado e limitação estão na seção seguinte. Produção, SLA e utilidade com usuários não são comprovados pelo laboratório.

## Resultado posterior à autorização Azure

A matriz acima foi registrada antes da implementação e preserva o diagnóstico original. A [rodada real](azure-live-results.md) demonstrou 47/48 resultados corretos com Luna, ante 24/48 do parser e 30/30 consultas estruturadas aplicáveis. Seis decisões de guardas locais permanecem no denominador do caminho modelo + backend, separadas das 42 chamadas finais. Houve um esclarecimento desnecessário e nenhuma falha crítica; todos os limiares prévios passaram. Smoke/desenvolvimento/final geraram 55 chamadas, 48.788 tokens e estimativa conservadora US$ 0,01550395. Acesso e orçamento foram fornecidos; produção e utilidade com usuários continuam não avaliados.
