# Fontes e afirmações — Loja Assistente

## Como ler a conferência

**Revisão das fontes: 22/09/2026.** Este registro reúne as referências do código, das decisões e dos resultados publicados. As datas nas tabelas identificam execuções, capturas e consultas de preços, não atualizações editoriais.

Os resultados de testes pertencem aos commits e ambientes indicados nos artefatos. Links para código e testes descrevem regras e critérios; exemplos sintéticos não comprovam resultados comerciais.

Em 22/09/2026, `python scripts/verify_evidence.py` conferiu 65 hashes de evidência, 62 fontes históricas, dois conjuntos de casos, denominadores e consumo, sem escrita, rede, banco ou provedor. Essa execução offline não reavaliou semanticamente o modelo.

## Regras e configuração atuais

| Afirmação                                                                    | Conclusão e fonte primária                                                                                                                                                                                                                      | Limite                                                             |
| ---------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Modelo interpreta; servidor autoriza e calcula                               | [Interpretação](../backend/src/loja_assistente/assistant/interpretation.py), [autorização](../backend/src/loja_assistente/auth/service.py) e [consultas](../backend/src/loja_assistente/analytics/queries.py)                                   | Plano válido não garante compreensão                               |
| Uma métrica; períodos 1–90 dias; ranking 1–20; até seis lojas                | [QueryPlan](../backend/src/loja_assistente/analytics/contracts.py) e [AskRequest](../backend/src/loja_assistente/assistant/contracts.py)                                                                                                        | IDs da pergunta têm limite 64, referências do plano 120 caracteres |
| Sem filtros de pagamento, vendedor, categoria, produto específico ou horário | [Guardas](../backend/src/loja_assistente/assistant/filter_limits.py), [contratos](../backend/src/loja_assistente/analytics/contracts.py) e [testes](../backend/tests/test_filter_limits.py)                                                     | Ranking não equivale a filtro individual                           |
| Centavos exatos, NUMERIC antes da multiplicação, ticket Decimal              | [SQL e razão](../backend/src/loja_assistente/analytics/queries.py), [modelo](../backend/src/loja_assistente/models.py) e [fronteiras numéricas](../backend/tests/test_money_contract.py)                                                        | Números extremos são contratos sintéticos                          |
| Ausência não vira zero; comparação exige cobertura completa                  | [Consulta](../backend/src/loja_assistente/analytics/queries.py) e [serviço](../backend/src/loja_assistente/analytics/service.py)                                                                                                                | —                                                                  |
| Fixture: R$ 30, dois pedidos, oito unidades e ticket R$ 15                   | [Fixture manual](../backend/tests/manual_fixture.py), [casos literais](../evals/cases/manual-v1.json) e [critérios](../backend/tests/test_analytics.py)                                                                                         | Não é a massa grande da interface                                  |
| Massa: 6.316 pedidos, 15.683 itens, 538 pares loja/dia em 90 dias            | [Manifesto](../data/manifests/synthetic-v1.json), [seed](../backend/src/loja_assistente/seed.py)                                                                                                                                                | Referência analítica 17/08/2026, dados fictícios                   |
| Aproximadamente 7% de cancelamentos                                          | Probabilidade configurada no [gerador](../backend/src/loja_assistente/seed.py), não estatística do varejo real                                                                                                                                  | Fração observada pode variar                                       |
| Corpo 16 KiB, prazo total do proxy 45 s                                      | [Leitura](../frontend/src/lib/server/request-body.ts), [prazo](../frontend/src/lib/server/proxy-lifetime.ts), [middleware API](../backend/src/loja_assistente/request_limits.py) e [critério de streams](../frontend/e2e/proxy-streams.spec.ts) | Cancelar fetch não prova interrupção no Python/provedor            |
| Banco: pool/conexão 5 s, statement 10 s, consulta analítica 3 s              | [Engine](../backend/src/loja_assistente/database.py) e [read_window](../backend/src/loja_assistente/analytics/queries.py)                                                                                                                       | Não é deadline total                                               |
| SDK 3.16.2; adaptador v5; até 1.000 tokens; timeout 12 s; sem retry          | [Lock](../backend/uv.lock) e [adaptador](../backend/src/loja_assistente/assistant/interpreters/openai_adapter.py)                                                                                                                               | Timeout de comunicação                                             |
| Reserva durável antes do despacho; incerteza conserva saldo                  | [Orçamento](../backend/src/loja_assistente/assistant/budget.py), [política](../backend/src/loja_assistente/assistant/budget_policy.py) e [testes](../backend/tests/test_budget_postgres.py)                                                     | Controla admissão, não fatura                                      |
| Demo sem LLM e serviços em loopback; PostgreSQL 17.11                        | [Compose](../compose.yaml) e [configuração](../backend/src/loja_assistente/config.py)                                                                                                                                                           | Padrão pode ser alterado localmente                                |

## Avaliação e custos históricos

| Dado apresentado                                                         | Fonte primária e conclusão                                                                                                                                                                                    | Data / limite                                                                       |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| 47/48 modelo + backend; 24/48 parser; 30/30 estruturado aplicável        | [summary.json](../evals/reports/20260921T121255Z-a9c11d1f/summary.json) e [cases.jsonl](../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl); conferidos pelo [verificador](../scripts/verify_evidence.py) | Executado em 21/09/2026; recalculado offline em 22/09/2026                          |
| 24 perguntas repetidas duas vezes; seis categorias; uma falha preservada | [Casos finais](../evals/cases/final-v1.json) e [execuções](../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl)                                                                                            | 21/09/2026; repetições não são exemplos independentes                               |
| 55 chamadas e 48.788 tokens no total                                     | [Chamadas históricas](evidence/azure-live/calls.md), resumos de smoke/desenvolvimento/final e verificador                                                                                                     | 21/09/2026; 45.307 entrada + 3.481 saída                                            |
| US$ 0,01550395 estimados                                                 | `45.307 × 0,25 / 1.000.000 + 3.481 × 1,20 / 1.000.000`; aritmética recalculada                                                                                                                                | Hipótese conservadora de 21/09/2026; não é fatura                                   |
| US$ 0,25/milhão não é o medidor de entrada normal                        | [Snapshot Azure](evidence/azure-live/azure-prices.json): normal 0,20; cache lido 0,02; cache escrito 0,25; saída 1,20, em USD/1M                                                                              | Consulta original 21/09/2026, vigência 01/08/2026, East US 2/GlobalStandard/ShortCo |
| Medidores de preço reconsultados em 22/09/2026                           | [Resposta pública de 22/09/2026](references/azure-prices-20260922.json), com URL oficial e itens retornados                                                                                                   | Não garante preço em outra região/modalidade/contrato nem custo futuro              |
| US$ 15 era teto autorizado da avaliação                                  | [Autorização histórica sanitizada](evidence/azure-live/connection-and-authorization.json) e [ledger do avaliador](../evals/live_budget.py)                                                                    | 21/09/2026; não é quota da conta Azure ou teto global da interface                  |
| p95 final 87 ms / 79 ms / 3.418 ms                                       | [Resumo final](../evals/reports/20260921T121255Z-a9c11d1f/summary.json), por caminho                                                                                                                          | 21/09/2026; ambiente/amostra limitados, sem navegador/SLA                           |

## Outras evidências e limites

| Afirmação                                               | Fonte e conclusão                                                                                                                                  | Data / limite                                                      |
| ------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| 69 casos Playwright = 39 puros + 30 navegador/HTTP      | [Recibo do CI](evidence/frontend-ci-20260922.json), commit `73aa1fff`                                                                              | 22/09/2026; resultado do commit indicado                           |
| Demais números de backend, orçamento e publicação       | [Índice de provas](evidence/operational-proof-20260922/index.json), [publicação](publication-check.json) e [histórico por rodada](verification.md) | 21–22/09/2026; não somar reexecuções como casos diferentes         |
| Evolução Centro: R$ 10.810,95, 56 pedidos, 227 unidades | [Resposta e sete linhas no manifesto](screenshots/current-20260922/capture.json); soma em centavos recalculada                                     | Captura de 22/09/2026; base `synthetic-v1`                         |
| EXPLAIN: 0,54 ms planejamento; 0,438 ms execução        | [query-plan.json](query-plan.json) registra PostgreSQL 17.6 e SQL anterior à promoção NUMERIC                                                      | Data/hora original ausente; observação única, não desempenho atual |
| Source Sans 3 local soma 170.188 bytes                  | [Arquivo e hashes](../frontend/src/app/fonts/sources.json), contagem dos bytes WOFF2                                                               | Não mede LCP/transferência                                         |
| Ganho de produtividade, produção e segurança universal  | Sem evidência demonstrada; [protocolo humano](usage-comparison.md) ainda é proposta                                                                | Não comprovado                                                     |

## Referências externas

| Referência                                                                                                                                                                                                          | O que sustenta                                                                                                                                 |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| [Microsoft — Structured Outputs](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/structured-outputs) e [endpoints](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/endpoints) | Contrato de transporte; não garante compreensão ou permissão                                                                                   |
| [OpenAI — saída estruturada](https://developers.openai.com/api/docs/guides/structured-outputs)                                                                                                                      | Schema, parsing e recusas; aplicado com validação local adicional                                                                              |
| [Azure Retail Prices API](https://prices.azure.com/api/retail/prices)                                                                                                                                               | Medidores públicos; consulta filtrada integral na [resposta guardada](references/azure-prices-20260922.json). Cobrança da conta não consultada |
| [PostgreSQL 17 — NUMERIC](https://www.postgresql.org/docs/17/datatype-numeric.html)                                                                                                                                 | Aritmética decimal exata; aplicação/limites dependem do código                                                                                 |
| [React — posição/chaves](https://react.dev/learn/preserving-and-resetting-state)                                                                                                                                    | Preservação de estado na árvore; não concede autorização                                                                                       |
| [OWASP — autorização](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)                                                                                                                | Orientação de validar permissão em cada requisição. Referência não equivale a auditoria completa                                               |

As referências visuais e sua aplicação estão em [frontend-quality.md](frontend-quality.md). São interpretações de design, não certificação de acessibilidade ou estudo de usabilidade.

## Ajustes desta revisão

- Arquitetura no README e ordem documental comum; rotas/objetos separados em tabelas.
- Rótulo de US$ 0,25 uniformizado como coeficiente conservador/escrita de cache. A tarifa normal de entrada é identificada separadamente, com fonte e data.
- EXPLAIN classificado como histórico de PostgreSQL 17.6 e SQL anterior; retirada a equivalência indevida com o código atual. Data de medição desconhecida declarada.
- Contagens genéricas “40+” removidas em favor dos artefatos identificados; resultados antigos não se tornam novos testes.
- `manual-fixture.md`, fontes congeladas, provas e relatórios hash-bound preservados byte a byte.

## Cobertura documental

Guias relacionados, com contratos, exemplos e evidências detalhados:

| Documento                                           | Conteúdo                                      |
| --------------------------------------------------- | --------------------------------------------- |
| [README.md](../README.md)                           | Apresentação, arquitetura e resumo com fontes |
| [docs/api-contract.md](api-contract.md)             | Contrato, configuração e critérios locais     |
| [docs/architecture.md](architecture.md)             | Contrato, configuração e critérios locais     |
| [docs/azure-live-results.md](azure-live-results.md) | Guia, decisões e resultados históricos        |
| [docs/data-contract.md](data-contract.md)           | Contrato, configuração e critérios locais     |
| [docs/decisoes-tecnicas.md](decisoes-tecnicas.md)   | Guia, decisões e resultados históricos        |
| [docs/demo-parser.md](demo-parser.md)               | Contrato, configuração e critérios locais     |
| [docs/demo.md](demo.md)                             | Guia, decisões e resultados históricos        |
| [docs/frontend-quality.md](frontend-quality.md)     | Guia, decisões e resultados históricos        |
| [docs/image-captures.md](image-captures.md)         | Guia, decisões e resultados históricos        |
| [docs/interface.md](interface.md)                   | Guia, decisões e resultados históricos        |
| [docs/live-evaluation.md](live-evaluation.md)       | Guia, decisões e resultados históricos        |
| [docs/llm-integration.md](llm-integration.md)       | Contrato, configuração e critérios locais     |
| [docs/local-setup.md](local-setup.md)               | Guia, decisões e resultados históricos        |
| [docs/metrics.md](metrics.md)                       | Contrato, configuração e critérios locais     |
| [docs/operational-story.md](operational-story.md)   | Guia, decisões e resultados históricos        |
| [docs/problem-solution.md](problem-solution.md)     | Guia, decisões e resultados históricos        |
| [docs/provider-budget.md](provider-budget.md)       | Contrato, configuração e critérios locais     |
| [docs/publication-check.md](publication-check.md)   | Guia, decisões e resultados históricos        |
| [docs/quality-review.md](quality-review.md)         | Guia, decisões e resultados históricos        |
| [docs/query-plan.md](query-plan.md)                 | Guia, decisões e resultados históricos        |
| [docs/security.md](security.md)                     | Guia, decisões e resultados históricos        |
| [docs/usage-comparison.md](usage-comparison.md)     | Guia, decisões e resultados históricos        |
| [docs/verification.md](verification.md)             | Guia, decisões e resultados históricos        |
| [evals/README.md](../evals/README.md)               | Guia, decisões e resultados históricos        |

Registros históricos, licenças e material ligado por hash conservam seus arquivos originais. O [padrão documental](padrao-documentacao.md) orienta a organização e a manutenção das referências.
