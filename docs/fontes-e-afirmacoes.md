# Fontes e afirmações — Loja Assistente

## Como ler a conferência

**Data da revisão documental: 22/09/2026.** Código, contratos e configuração foram confrontados com as fontes locais indicadas; números históricos foram conferidos nos artefatos preservados. A data de conferência não substitui a data da execução. Exemplos sintéticos, configurações padrão, observações históricas e propostas futuras têm naturezas diferentes.

Esta revisão não reexecutou a aplicação, suítes de backend/navegador, scans de segurança, restauração ou estudos de usuários. Os números de testes continuam restritos aos commits/ambientes originais. Links para código/testes mostram regra e critério; não significam que o teste foi executado agora. Valores ilustrativos não comprovam resultado comercial.

Nesta rodada, `python scripts/verify_evidence.py` foi executado **sem escrita, rede, banco ou provedor**: conferiu 65 hashes de evidência, 62 fontes históricas, dois conjuntos de casos, denominadores e consumo. Essa conferência não é uma nova avaliação semântica do código atual.

## Regras e configuração atuais

| Afirmação                                                                    | Conclusão e fonte primária                                                                                                                                                                                                                      | Data / limite                                                                               |
| ---------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Modelo interpreta; servidor autoriza e calcula                               | [Interpretação](../backend/src/loja_assistente/assistant/interpretation.py), [autorização](../backend/src/loja_assistente/auth/service.py) e [consultas](../backend/src/loja_assistente/analytics/queries.py)                                   | Conferido em 22/09/2026; plano válido não garante compreensão                               |
| Uma métrica; períodos 1–90 dias; ranking 1–20; até seis lojas                | [QueryPlan](../backend/src/loja_assistente/analytics/contracts.py) e [AskRequest](../backend/src/loja_assistente/assistant/contracts.py)                                                                                                        | Conferido em 22/09/2026; IDs da pergunta têm limite 64, referências do plano 120 caracteres |
| Sem filtros de pagamento, vendedor, categoria, produto específico ou horário | [Guardas](../backend/src/loja_assistente/assistant/filter_limits.py), [contratos](../backend/src/loja_assistente/analytics/contracts.py) e [testes](../backend/tests/test_filter_limits.py)                                                     | Conferido em 22/09/2026; ranking não equivale a filtro individual                           |
| Centavos exatos, NUMERIC antes da multiplicação, ticket Decimal              | [SQL e razão](../backend/src/loja_assistente/analytics/queries.py), [modelo](../backend/src/loja_assistente/models.py) e [fronteiras numéricas](../backend/tests/test_money_contract.py)                                                        | Conferido em 22/09/2026; números extremos são contratos sintéticos                          |
| Ausência não vira zero; comparação exige cobertura completa                  | [Consulta](../backend/src/loja_assistente/analytics/queries.py) e [serviço](../backend/src/loja_assistente/analytics/service.py)                                                                                                                | Conferido em 22/09/2026                                                                     |
| Fixture: R$ 30, dois pedidos, oito unidades e ticket R$ 15                   | [Fixture manual](../backend/tests/manual_fixture.py), [casos literais](../evals/cases/manual-v1.json) e [critérios](../backend/tests/test_analytics.py)                                                                                         | Conferido em 22/09/2026; não é a massa grande da interface                                  |
| Massa: 6.316 pedidos, 15.683 itens, 538 pares loja/dia em 90 dias            | [Manifesto](../data/manifests/synthetic-v1.json), [seed](../backend/src/loja_assistente/seed.py)                                                                                                                                                | Conferido em 22/09/2026; referência analítica 17/08/2026, dados fictícios                   |
| Aproximadamente 7% de cancelamentos                                          | Probabilidade configurada no [gerador](../backend/src/loja_assistente/seed.py), não estatística do varejo real                                                                                                                                  | Conferido em 22/09/2026; fração observada pode variar                                       |
| Corpo 16 KiB, prazo total do proxy 45 s                                      | [Leitura](../frontend/src/lib/server/request-body.ts), [prazo](../frontend/src/lib/server/proxy-lifetime.ts), [middleware API](../backend/src/loja_assistente/request_limits.py) e [critério de streams](../frontend/e2e/proxy-streams.spec.ts) | Conferido em 22/09/2026; cancelar fetch não prova interrupção no Python/provedor            |
| Banco: pool/conexão 5 s, statement 10 s, consulta analítica 3 s              | [Engine](../backend/src/loja_assistente/database.py) e [read_window](../backend/src/loja_assistente/analytics/queries.py)                                                                                                                       | Conferido em 22/09/2026; não é deadline total                                               |
| SDK 3.16.2; adaptador v5; até 1.000 tokens; timeout 12 s; sem retry          | [Lock](../backend/uv.lock) e [adaptador](../backend/src/loja_assistente/assistant/interpreters/openai_adapter.py)                                                                                                                               | Conferido em 22/09/2026; timeout de comunicação                                             |
| Reserva durável antes do despacho; incerteza conserva saldo                  | [Orçamento](../backend/src/loja_assistente/assistant/budget.py), [política](../backend/src/loja_assistente/assistant/budget_policy.py) e [testes](../backend/tests/test_budget_postgres.py)                                                     | Conferido em 22/09/2026; controla admissão, não fatura                                      |
| Demo sem LLM e serviços em loopback; PostgreSQL 17.11                        | [Compose](../compose.yaml) e [configuração](../backend/src/loja_assistente/config.py)                                                                                                                                                           | Conferido em 22/09/2026; padrão pode ser alterado localmente                                |

## Avaliação e custos históricos

| Dado apresentado                                                         | Fonte primária e conclusão                                                                                                                                                                                    | Data / limite                                                                       |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| 47/48 modelo + backend; 24/48 parser; 30/30 estruturado aplicável        | [summary.json](../evals/reports/20260921T121255Z-a9c11d1f/summary.json) e [cases.jsonl](../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl); conferidos pelo [verificador](../scripts/verify_evidence.py) | Executado em 21/09/2026; recalculado offline em 22/09/2026                          |
| 24 perguntas repetidas duas vezes; seis categorias; uma falha preservada | [Casos finais](../evals/cases/final-v1.json) e [execuções](../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl)                                                                                            | 21/09/2026; repetições não são exemplos independentes                               |
| 55 chamadas e 48.788 tokens no total                                     | [Chamadas históricas](evidence/azure-live/calls.md), resumos de smoke/desenvolvimento/final e verificador                                                                                                     | 21/09/2026; 45.307 entrada + 3.481 saída; sem novos gastos nesta revisão            |
| US$ 0,01550395 estimados                                                 | `45.307 × 0,25 / 1.000.000 + 3.481 × 1,20 / 1.000.000`; aritmética recalculada                                                                                                                                | Hipótese conservadora de 21/09/2026, reconferida em 22/09/2026; não é fatura        |
| US$ 0,25/milhão não é o medidor de entrada normal                        | [Snapshot Azure](evidence/azure-live/azure-prices.json): normal 0,20; cache lido 0,02; cache escrito 0,25; saída 1,20, em USD/1M                                                                              | Consulta original 21/09/2026, vigência 01/08/2026, East US 2/GlobalStandard/ShortCo |
| Mesmos medidores encontrados na revisão                                  | [Resposta pública de 22/09/2026](references/azure-prices-20260922.json), com URL oficial e itens retornados                                                                                                   | Não garante preço em outra região/modalidade/contrato nem custo futuro              |
| US$ 15 era teto autorizado da avaliação                                  | [Autorização histórica sanitizada](evidence/azure-live/connection-and-authorization.json) e [ledger do avaliador](../evals/live_budget.py)                                                                    | 21/09/2026; não é quota da conta Azure ou teto global da interface                  |
| p95 final 87 ms / 79 ms / 3.418 ms                                       | [Resumo final](../evals/reports/20260921T121255Z-a9c11d1f/summary.json), por caminho                                                                                                                          | 21/09/2026; ambiente/amostra limitados, sem navegador/SLA                           |

## Outras evidências e limites

| Afirmação                                               | Fonte e conclusão                                                                                                                                  | Data / limite                                                                               |
| ------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| 69 casos Playwright = 39 puros + 30 navegador/HTTP      | [Recibo do CI](evidence/frontend-ci-20260922.json), commit `73aa1fff`                                                                              | 22/09/2026; sem nova suíte nesta revisão                                                    |
| Demais números de backend, orçamento e publicação       | [Índice de provas](evidence/operational-proof-20260922/index.json), [publicação](publication-check.json) e [histórico por rodada](verification.md) | 21–22/09/2026; não somar reexecuções como casos diferentes                                  |
| Evolução Centro: R$ 10.810,95, 56 pedidos, 227 unidades | [Resposta e sete linhas no manifesto](screenshots/current-20260922/capture.json); soma em centavos recalculada                                     | Captura de 22/09/2026; base `synthetic-v1`                                                  |
| EXPLAIN: 0,54 ms planejamento; 0,438 ms execução        | [query-plan.json](query-plan.json) registra PostgreSQL 17.6 e SQL anterior à promoção NUMERIC                                                      | Data/hora original ausente; conferido em 22/09/2026; observação única, não desempenho atual |
| Source Sans 3 local soma 170.188 bytes                  | [Arquivo e hashes](../frontend/src/app/fonts/sources.json), contagem dos bytes WOFF2                                                               | Recalculado em 22/09/2026; não mede LCP/transferência                                       |
| Ganho de produtividade, produção e segurança universal  | Sem evidência demonstrada; [protocolo humano](usage-comparison.md) ainda é proposta                                                                | Não comprovado em 22/09/2026                                                                |

A consulta à API pública do GitHub em **22/09/2026** confirmou `conclusion=success` e o mesmo SHA do [recibo de CI](evidence/frontend-ci-20260922.json). Isso valida a identidade e conclusão daquele run, sem repetir seus testes.

## Referências externas

| Referência                                                                                                                                                                                                          | O que sustenta                                                                                               | Consulta                                                 |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------- |
| [Microsoft — Structured Outputs](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/structured-outputs) e [endpoints](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/endpoints) | Contrato de transporte; não garante compreensão ou permissão                                                 | 22/09/2026                                               |
| [OpenAI — saída estruturada](https://developers.openai.com/api/docs/guides/structured-outputs)                                                                                                                      | Schema, parsing e recusas; aplicado com validação local adicional                                            | 22/09/2026                                               |
| [Azure Retail Prices API](https://prices.azure.com/api/retail/prices)                                                                                                                                               | Medidores públicos; consulta filtrada integral na [resposta guardada](references/azure-prices-20260922.json) | 22/09/2026; cobrança da conta não consultada             |
| [PostgreSQL 17 — NUMERIC](https://www.postgresql.org/docs/17/datatype-numeric.html)                                                                                                                                 | Aritmética decimal exata; aplicação/limites dependem do código                                               | 22/09/2026                                               |
| [React — posição/chaves](https://react.dev/learn/preserving-and-resetting-state)                                                                                                                                    | Preservação de estado na árvore; não concede autorização                                                     | 22/09/2026                                               |
| [OWASP — autorização](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)                                                                                                                | Orientação de validar permissão em cada requisição                                                           | 22/09/2026; referência não equivale a auditoria completa |

Referências visuais, datas e interpretações autorais estão em [frontend-quality.md](frontend-quality.md). Reconsultados em 22/09/2026: Lightdash, Superset, Linear, Carbon, Atlassian, Radix, Pentagram, Behance/Swavee, React e W3C. A demo externa Lightdash não foi usada como nova prova de comportamento local.

## Ajustes desta revisão

- Arquitetura no README e ordem documental comum; rotas/objetos separados em tabelas.
- Rótulo de US$ 0,25 uniformizado como coeficiente conservador/escrita de cache. A tarifa normal de entrada é identificada separadamente, com fonte e data.
- EXPLAIN classificado como histórico de PostgreSQL 17.6 e SQL anterior; retirada a equivalência indevida com o código atual. Data de medição desconhecida declarada.
- Contagens genéricas “40+” removidas em favor dos artefatos identificados; resultados antigos não se tornam novos testes.
- `manual-fixture.md`, fontes congeladas, provas e relatórios hash-bound preservados byte a byte.

## Cobertura documental

Todos os Markdown vivos abaixo foram revisados quanto a hierarquia, contratos, números, proveniência, data e links. Referências e datas ficam também junto às seções correspondentes.

| Documento                                           | Escopo da revisão                                            |
| --------------------------------------------------- | ------------------------------------------------------------ |
| [README.md](../README.md)                           | Apresentação, arquitetura e resumo com fontes                |
| [docs/api-contract.md](api-contract.md)             | Contrato, configuração ou critérios locais; fontes por seção |
| [docs/architecture.md](architecture.md)             | Contrato, configuração ou critérios locais; fontes por seção |
| [docs/azure-live-results.md](azure-live-results.md) | Guia, decisões ou histórico; data e alcance explicitados     |
| [docs/data-contract.md](data-contract.md)           | Contrato, configuração ou critérios locais; fontes por seção |
| [docs/decisoes-tecnicas.md](decisoes-tecnicas.md)   | Guia, decisões ou histórico; data e alcance explicitados     |
| [docs/demo-parser.md](demo-parser.md)               | Contrato, configuração ou critérios locais; fontes por seção |
| [docs/demo.md](demo.md)                             | Guia, decisões ou histórico; data e alcance explicitados     |
| [docs/frontend-quality.md](frontend-quality.md)     | Guia, decisões ou histórico; data e alcance explicitados     |
| [docs/image-captures.md](image-captures.md)         | Guia, decisões ou histórico; data e alcance explicitados     |
| [docs/interface.md](interface.md)                   | Guia, decisões ou histórico; data e alcance explicitados     |
| [docs/live-evaluation.md](live-evaluation.md)       | Guia, decisões ou histórico; data e alcance explicitados     |
| [docs/llm-integration.md](llm-integration.md)       | Contrato, configuração ou critérios locais; fontes por seção |
| [docs/local-setup.md](local-setup.md)               | Guia, decisões ou histórico; data e alcance explicitados     |
| [docs/metrics.md](metrics.md)                       | Contrato, configuração ou critérios locais; fontes por seção |
| [docs/operational-story.md](operational-story.md)   | Guia, decisões ou histórico; data e alcance explicitados     |
| [docs/problem-solution.md](problem-solution.md)     | Guia, decisões ou histórico; data e alcance explicitados     |
| [docs/provider-budget.md](provider-budget.md)       | Contrato, configuração ou critérios locais; fontes por seção |
| [docs/publication-check.md](publication-check.md)   | Guia, decisões ou histórico; data e alcance explicitados     |
| [docs/quality-review.md](quality-review.md)         | Guia, decisões ou histórico; data e alcance explicitados     |
| [docs/query-plan.md](query-plan.md)                 | Guia, decisões ou histórico; data e alcance explicitados     |
| [docs/security.md](security.md)                     | Guia, decisões ou histórico; data e alcance explicitados     |
| [docs/usage-comparison.md](usage-comparison.md)     | Guia, decisões ou histórico; data e alcance explicitados     |
| [docs/verification.md](verification.md)             | Guia, decisões ou histórico; data e alcance explicitados     |
| [evals/README.md](../evals/README.md)               | Guia, decisões ou histórico; data e alcance explicitados     |

Registros históricos, licenças e material ligado por hash foram conferidos como fontes, mas não reformatados. O [padrão documental](padrao-documentacao.md) define a ordem e como manter novas afirmações rastreáveis.
