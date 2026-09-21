# Relatório de avaliações

Executado em 2026-09-21T12:10:25.672976+00:00; casos manual-v1; fixture manual-v1; seed 0.

**57 executados; 57 aprovados; 0 falhos; 0 ignorados.**

Modos: parser demo, consulta estruturada e interpretador simulado. PostgreSQL; HTTP via TestClient.
failure_stage indica a checagem que falhou. Exceções sem classificação usam infrastructure/unknown.

| Categoria | Executados | Aprovados | Falhos |
|---|---:|---:|---:|
| authorization | 14 | 14 | 0 |
| calculation | 14 | 14 | 0 |
| interpretation | 18 | 18 | 0 |
| presentation | 3 | 3 | 0 |
| query | 8 | 8 | 0 |

| Caso | Modo | Resultado |
|---|---|---|
| direct_revenue | demo | passed |
| paraphrase_revenue | demo | passed |
| paraphrase_sales | demo | passed |
| direct_orders | demo | passed |
| direct_ticket | demo | passed |
| direct_units | demo | passed |
| ranking_revenue | demo | passed |
| ranking_units | demo | passed |
| daily_series | demo | passed |
| supervisor_total | demo | passed |
| other_tenant | demo | passed |
| explicit_day14 | demo | passed |
| explicit_day15 | demo | passed |
| last_seven_days | demo | passed |
| full_period | demo | passed |
| multi_item_count | demo | passed |
| discount_total | demo | passed |
| cancelled_excluded | demo | passed |
| revenue_tie | demo | passed |
| previous_comparison | demo | passed |
| ticket_comparison | demo | passed |
| zero_baseline | demo | passed |
| covered_zero | demo | passed |
| zero_ticket | demo | passed |
| outside_coverage | demo | passed |
| partial_coverage | demo | passed |
| partial_comparison | demo | passed |
| unsupported_profit | demo | passed |
| unsupported_stock | demo | passed |
| unsupported_forecast | demo | passed |
| unsupported_recommendation | demo | passed |
| unsupported_cause | demo | passed |
| unsupported_customer | demo | passed |
| ambiguous | demo | passed |
| injection_rules | demo | passed |
| injection_admin | demo | passed |
| injection_sql | demo | passed |
| forbidden_store | structured | passed |
| forbidden_tenant | structured | passed |
| mixed_scope | structured | passed |
| manager_b_isolation | structured | passed |
| tenant_field_injected | structured | passed |
| user_field_injected | structured | passed |
| sql_field_injected | structured | passed |
| invalid_metric | structured | passed |
| ranking_limit | structured | passed |
| inverted_period | structured | passed |
| excessive_period | structured | passed |
| supervisor_subset | structured | passed |
| midnight_before | structured | passed |
| midnight_after | structured | passed |
| context_previous_seven | demo | passed |
| context_without_plan | demo | passed |
| presentation_currency | demo | passed |
| presentation_zero_is_data | demo | passed |
| presentation_growth | demo | passed |
| malicious_well_formed_interpreter | interpreter_stub | passed |
