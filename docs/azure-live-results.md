# Avaliação com Azure Foundry

Resultados da avaliação de 21/09/2026. O [verificador offline](../scripts/verify_evidence.py) passou novamente em 22/09/2026, sem reavaliar o modelo.

Este relatório descreve a **versão avaliada em 21/09/2026**. O orçamento persistente foi acrescentado depois e tem [prova própria, com provedor simulado](provider-budget.md). Os 47/48 abaixo não são uma nova avaliação semântica do código atual.

Para manter o resultado conferível após a evolução do código, o [manifesto histórico](evidence/azure-live/historical-source-20260921.json) associa 62 arquivos de fonte e dois conjuntos de casos aos bytes originais, preservados em `docs/evidence/azure-live/source-20260921/`. O verificador compara esse arquivo histórico ao freeze original e aos 65 artefatos publicados; alterações no código ativo são informadas separadamente. Não houve nova chamada Azure para produzir esse arquivo.

Em 21/09/2026, a integração com GPT-5.6 Luna, versão 2026-07-09, passou na avaliação final definida antes da execução. Recurso em East US 2, deployment GlobalStandard; inferência por Azure OpenAI v1. Usei um recurso Azure próprio, com teto de US$ 15 para a avaliação; nenhum recurso novo foi provisionado. A chave fica no `.env` ignorado.

O problema é transformar português variado em uma consulta financeira correta e autorizada. O modelo interpreta intenção, lojas e datas; o PostgreSQL calcula. Não há SQL gerado pelo modelo nem números financeiros escritos por ele.

Para conferir no repositório: [perguntas e resultados lado a lado](evidence/azure-live/cases.md), [chamadas com IDs e tokens](evidence/azure-live/calls.md) e [índice de logs e verificação offline](evidence/README.md).

## Resultado comparável

| Caminho                | Desenvolvimento |  Avaliação final | p95 final |
| ---------------------- | --------------: | ---------------: | --------: |
| Parser offline         |           12/12 |            24/48 |     87 ms |
| Filtros estruturados   |  9/9 aplicáveis | 30/30 aplicáveis |     79 ms |
| Modelo Azure + backend |           12/12 |   47/48 (97,92%) |  3.418 ms |

A amostra final contém 24 perguntas distintas, repetidas duas vezes, e não 48 exemplos independentes. São seis categorias, com quatro perguntas em cada uma. Consultas estruturadas só se aplicam aos 15 casos executáveis; os nove casos de recusa não entram nesse denominador. O caminho com modelo inclui 42 chamadas reais e seis recusas por guardas locais, de três perguntas sobre Pix, horário e categoria. Essas guardas não foram contabilizadas como chamadas de IA.

| Categoria final        | Parser | Modelo + backend |
| ---------------------- | -----: | ---------------: |
| Linguagem natural      |    0/8 |              8/8 |
| Período e contexto     |    0/8 |              8/8 |
| Escopo de lojas        |    4/8 |              8/8 |
| Filtros não suportados |    8/8 |              8/8 |
| Ambiguidade e saudação |    8/8 |              8/8 |
| Fronteiras e finanças  |    4/8 |              7/8 |

Nos casos medidos: zero violações de autorização, zero aceitação de filtro não representado e zero divergências financeiras em resultados retornados. O avaliador confere o plano, o resultado, os dados guardados e as consultas analíticas; HTTP 200 isoladamente não aprova. Depois da execução, as contagens foram recalculadas e os valores literais conferidos contra a fixture ([final-review.json](evidence/azure-live/final-review.json)).

O resultado atende aos critérios definidos antes: semântica total ≥90%, cada categoria ≥80%, esclarecimentos desnecessários ≤10% dos executáveis e zero falhas críticas. Latência inclui autenticação sintética, ASGI, rede Azure e PostgreSQL; não inclui navegador nem representa SLA de produção.

## Falha registrada

`final-bf-04`, repetição 2: “Qual foi a receita de 09 a 14/08/2026? Pode indicar os dias que não foram carregados.” O modelo pediu esclarecimento porque entendeu que não poderia informar cobertura, embora o backend já forneça os dias ausentes. Não houve plano, resultado nem consulta analítica. A primeira repetição acertou.

É um esclarecimento desnecessário: 1/30 executáveis (3,33%). O prompt não foi ajustado depois de ler o holdout e a avaliação não foi repetida para apagar a falha. Uma correção futura exige guardar este resultado e preparar nova avaliação com casos novos.

## Chamadas e consumo

- [Smoke real](../evals/reports/20260921T121119Z-883376fa/summary.md): uma chamada, aprovado.
- [Desenvolvimento real](../evals/reports/20260921T121149Z-c53a402a/summary.md): 12 chamadas, aprovado.
- [Avaliação final](../evals/reports/20260921T121255Z-a9c11d1f/summary.md): 42 chamadas, `live_final_approved`.
- [Esperado, observado e metadata por caso](../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl), [resumo estruturado](../evals/reports/20260921T121255Z-a9c11d1f/summary.json), [fontes congeladas](evidence/azure-live/freeze-azure-luna-r1.json).
- [Preços oficiais consultados](evidence/azure-live/azure-prices.json), [descoberta e autorização sem chave](evidence/azure-live/connection-and-authorization.json), [comando final e exit code](evidence/azure-live/final-command.json).
- [Conferência final](evidence/azure-live/final-review.json): contagens conferidas, fonte congelada consistente, 103 links locais válidos e nenhuma ocorrência da chave nos 198 arquivos públicos examinados.

Total das três etapas: 55 chamadas, todas concluídas sem retries; 45.307 tokens de entrada + 3.481 de saída = 48.788 tokens, sem uso desconhecido. Estimativa conservadora US$ 0,01550395; reserva persistida US$ 0,23306975. O limite de tentativas era 61 e o teto autorizado US$ 15.

A estimativa usa US$ 0,25/milhão para toda entrada, cobrindo a tarifa publicada de escrita de cache, e US$ 1,20/milhão para saída. Entrada normal custa US$ 0,20/milhão e leitura de cache US$ 0,02/milhão; descontos não foram presumidos. A [Azure Retail Prices API](https://prices.azure.com/api/retail/prices) foi consultada em 21/09/2026 para East US 2/GlobalStandard, com vigência dos medidores desde 01/08/2026. A [reconsulta dos medidores em 22/09/2026](references/azure-prices-20260922.json) encontrou os mesmos valores para essa região/modalidade; não altera o cálculo histórico. Não é uma fatura: cobrança efetiva da conta não foi consultada.

## Implementação entregue

O adaptador v5 usa Responses, `reasoning=none`, contrato JSON estrito, até 1.000 tokens de saída, `store=false`, timeout de comunicação de 12 s e zero retries. Retira do schema enviado somente palavras-chave não suportadas pela Azure; Pydantic mantém datas, limites, capacidades e propriedades proibidas antes de autorização/SQL. O hash identifica o schema efetivamente enviado. Esforço omitido continua disponível para deployments sem esse parâmetro.

Também foram corrigidos os relatórios de falhas de preparação do banco, lock, conexão e seed: registram etapa, classe do erro, resultado reprovado e limpeza, sem texto de exceção que possa conter segredo. 313 testes backend passaram, mais Ruff/formato/mypy e 57/57 regressões já incluídas na suíte. [Log dos testes](evidence/azure-live/backend-checks.log). A suíte de navegador tem 47 casos; esta integração não mudou o frontend.

Na instância usada nesta avaliação, o modelo real estava habilitado e disponível no campo Interpretador. Um novo clone inicia com `LLM_ENABLED=false` e oferece o parser como Demonstração (sem IA). Para habilitar o modelo, siga a [configuração OpenAI/Azure](llm-integration.md). O teto de US$ 15 valeu só para esta avaliação; não é uma quota global da conta Azure nem um limite monetário da interface. Com o modelo habilitado, chamadas posteriores pela interface usam a credencial local.

Código, prompt e schema foram congelados às 12:11:13 UTC, antes do smoke; os 24 casos finais foram escritos antes do freeze e só executados depois. O freeze anterior foi guardado. A base ilustrativa da interface é diferente da fixture manual usada na avaliação; seus valores não devem ser comparados diretamente.

Isto mostra integração real e correção técnica na amostra. Utilidade com usuários, ganhos comerciais, operação em produção e segurança universal continuam não avaliados. [Protocolo para uma nova avaliação](live-evaluation.md) e [decisões técnicas](decisoes-tecnicas.md).

## Verificação da entrega local

[Runtime, imagem e dados guardados](evidence/azure-live/runtime-verification.json): API e interface retornam HTTP 200; 61 arquivos de fonte dentro da imagem correspondem ao freeze; .env e .runtime não estão incorporados na imagem. Os hashes e contagens de 11 tabelas foram guardados, incluindo 6.316 pedidos, 15.683 itens, 74 conversas e 118 respostas. O navegador confirmou a opção Modelo de IA disponível e selecionada; nenhuma chamada extra foi feita nessa conferência de disponibilidade. O banco temporário da avaliação foi parado.
