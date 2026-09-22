# Comparar a consulta em português com os controles

> Protocolo proposto, sem participantes ou resultados humanos. Fontes: [casos de treino](../evals/cases/manual-v1.json), [formulário da rodada](user-study/round.template.json) e [formulário de observação](user-study/observation.template.json). Conferência documental: **22/09/2026**.

**Pergunta central:** uma pessoa consegue chegar ao recorte correto e conferir o cálculo com menos esforço? Acertar um plano em teste automático é necessário, mas não responde essa pergunta de uso.

**Estado: protocolo preparado, sem participantes ou resultados.** Não houve medição de produtividade nesta rodada. A avaliação histórica de 47/48 tentativas trata interpretação e cálculo em 24 perguntas repetidas duas vezes; não mede tempo humano e não será reapresentada como estudo novo. A falha `final-bf-04`, repetição 2, permanece no [resultado original](azure-live-results.md).

## O que comparar

| Condição                           | Tarefa da pessoa                                                                                    | Limite da comparação                                                                                                                   |
| ---------------------------------- | --------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Pergunta em português              | Formular a pergunta, conferir lojas/período aplicados e abrir o cálculo                             | Registrar se usou parser demo ou modelo, com versão e configuração                                                                     |
| Controles da interface             | Escolher lojas/período nos controles e usar uma pergunta canônica previamente fixada para a métrica | A aplicação ainda exige uma pergunta; esta é uma baseline de controles no mesmo produto, não um dashboard independente já implementado |
| Consulta estruturada de referência | Avaliador confere plano e resultado contra o esperado                                               | É oráculo de correção; não mede o esforço de uma pessoa                                                                                |

As duas condições de uso precisam oferecer a mesma informação, permissão e tarefa. Um dashboard externo só entra na comparação depois de implementado/configurado e conferido com a mesma base; não usar um tempo imaginado para ele. Nenhuma condição pode receber uma loja ou data pronta que a outra precise descobrir, salvo se essa diferença for o objeto explícito do experimento.

## Preparar uma rodada

1. Concluir as [jornadas da interface](verification.md), fixar commit/imagens, dataset, fuso, data de referência, navegador, viewport e modo de interpretação. A versão do modelo precisa ser registrada se ele for usado; gasto exige orçamento/configuração próprios, sem reutilizar a autorização histórica encerrada.
2. Preparar tarefas de desenvolvimento para explicar o exercício e tarefas novas de avaliação antes da coleta. Os casos já publicados ou usados para ajustar a solução são desenvolvimento. Não chamar o holdout histórico, já conhecido, de conjunto não visto novamente.
3. Para cada tarefa, guardar plano esperado, lojas permitidas, início/fim exclusivo, cobertura e resultado calculado independentemente. O participante recebe o objetivo, sem gabarito ou pergunta canônica da outra condição.
4. Distribuir a ordem entre condições e tarefas equivalentes para reduzir memorização. Registrar a ordem real; com uma só pessoa, declarar que aprendizado e preferência podem dominar o resultado. Não há tamanho de amostra ou representatividade comprovados previamente.
5. Preencher o [formulário da rodada](user-study/round.template.json) antes da coleta e um [registro por tarefa](user-study/observation.template.json) após cada tentativa. Usar identificadores de participantes; manter dados pessoais e registros completos em local privado, publicando apenas resumo autorizado.

## Exemplos de treino conferíveis

Estes exemplos usam a [fixture manual](manual-fixture.md), **não a carteira grande do setup**. Referência comercial: 17/08/2026, `America/Sao_Paulo`. São exercícios conhecidos para preparar a rodada, não resultados de participantes.

| Objetivo                                | Identidade/recorte                                 | Esperado independente                                                             |
| --------------------------------------- | -------------------------------------------------- | --------------------------------------------------------------------------------- |
| Conferir receita e cálculo de ontem     | Gerente A, Centro A, 16/08 com fim exclusivo 17/08 | 3.000 centavos, 2 pedidos e 8 unidades; ticket 1.500 centavos                     |
| Entender a evolução sem mudar a métrica | Gerente A, Centro A, 14–16/08                      | Série de receita `[2500, 1600, 3000]` centavos                                    |
| Distinguir ausência de zero             | Centro A, 09/08 versus 10/08                       | 09/08 sem cobertura: indisponível; 10/08 carregado sem vendas: zero               |
| Reconhecer limite do produto            | Pedido de lucro                                    | Recusa/esclarecimento explícito; não substituir lucro por receita silenciosamente |

A pessoa deve apontar o recorte **do resultado executado**, não apenas os filtros atualmente selecionados para a próxima pergunta. Abrir gráfico, texto e tabela deve permitir conferir o mesmo cálculo, sem tratar três apresentações como três respostas independentes.

## Registrar sem favorecer o resultado

- Começar o tempo ao apresentar a tarefa e encerrar quando a pessoa declarar que terminou ou atingir o limite previamente fixado. Separar espera do sistema, quando observável, sem subtrair pausas por decisão posterior.
- Registrar conclusão correta, resposta errada, desistência, timeout e tarefa não iniciada separadamente. Recusa correta de capacidade inexistente conta conforme o gabarito dessa tarefa, não como sucesso financeiro.
- Conferir métrica, autorização, lojas, período, cobertura e valor. Resposta numericamente igual com recorte errado não passa. Guardar request/answer IDs para associar a observação ao resultado persistido.
- Registrar ajuda, reformulações, cliques e dúvidas com critério fixado antes. O autor orientando a pessoa é intervenção; não esconder essa ajuda para aparentar autonomia.
- Campos ainda não observados ficam `null`, nunca zero, sucesso ou aprovação. Feedback é opinião identificada; não é medida de ganho financeiro.

## Interpretar e decidir

Apresentar primeiro quantas pessoas e tarefas realmente participaram, distribuição dos tempos observados, taxa de recorte correto e erros por condição. Manter tarefas incompletas no total planejado. Evitar percentuais de ganho com poucos casos ou exclusão de tentativas lentas; comparações por pessoa não tornam suas várias perguntas participantes independentes.

Se a pergunta em português poupar entrada mas aumentar erros de recorte, a decisão pode ser melhorar confirmação/clareza ou priorizar controles. Se as condições não diferirem de forma confiável, registrar isso. O protocolo testa uma hipótese de utilidade; não estabelece antecipadamente que IA, parser ou formulário será superior.
