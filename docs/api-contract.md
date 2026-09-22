# Contrato HTTP e integração interna

Todos os caminhos possuem prefixo `/api`; Next.js faz proxy para o backend. Erros HTTP usam `detail` textual. Cookie de sessão: `la_session`. POST exige `Origin` permitido; depois do login também exige `X-CSRF-Token`. JSON usa `snake_case`.

## Rotas

Fontes do contrato local: [`routes.py`](../backend/src/loja_assistente/auth/routes.py), [`routes.py`](../backend/src/loja_assistente/assistant/routes.py), [`routes.py`](../backend/src/loja_assistente/conversations/routes.py), [`routes.py`](../backend/src/loja_assistente/observability/routes.py). Conferência documental em **22/09/2026**; regras da implementação, não medição de produção.

| Método e caminho             | Entrada                               | Retorno                                                                     |
| ---------------------------- | ------------------------------------- | --------------------------------------------------------------------------- |
| `POST /auth/login`           | `email`, `password`                   | Mesmo objeto de `/auth/me`, com cookie                                      |
| `GET /auth/me`               | Sessão                                | Usuário, `csrf_token`, `reference_date`, `dataset_version`, `llm_available` |
| `POST /auth/logout`          | Sessão e CSRF                         | `ok: true`                                                                  |
| `GET /conversations`         | Sessão                                | Conversas com `id`, `title`, `created_at`                                   |
| `POST /conversations`        | Objeto vazio                          | `id`, `title`, `created_at`                                                 |
| `GET /conversations/{id}`    | ID                                    | Identificação da conversa e `messages`, lista de respostas                  |
| `POST /assistant/query`      | Pergunta e contexto                   | Resposta (`Answer`)                                                         |
| `POST /analytics/query`      | Plano (`QueryPlan`), CSRF obrigatório | Resultado (`AnalyticsResult`)                                               |
| `GET /answers/{id}`          | ID                                    | Resposta                                                                    |
| `GET /answers/{id}/evidence` | ID                                    | Resultado autorizado                                                        |
| `GET /operations`            | Sessão                                | `entries`, `total`, `errors`, `tokens: null`, `cost: null`                  |
| `GET /health`                | —                                     | `status: "ok"`; prontidão verifica `SELECT 1`                               |

O usuário de `/auth/me` contém `id`, `name`, `email`, `role`, `organization` (`id`, `name`) e `stores` (lista de `id`, `name`). Cada entrada operacional contém `request_id`, `mode`, `capability`, `status`, `interpretation_ms`, `query_ms`, `response_ms`, `created_at` e `interpreter_version`.

## Pergunta e plano

Fontes do contrato local: [`contracts.py`](../backend/src/loja_assistente/analytics/contracts.py), [`contracts.py`](../backend/src/loja_assistente/assistant/contracts.py). Conferência documental em **22/09/2026**; regras da implementação, não medição de produção.

| Entrada da pergunta | Interpretação                        |
| ------------------- | ------------------------------------ |
| `question`          | Texto da pergunta                    |
| `conversation_id`   | ID textual ou `null`                 |
| `mode`              | `demo` ou `llm`                      |
| `store_ids`         | Lista de IDs de lojas                |
| `period`            | `null` ou objeto com `start` e `end` |

| Campo do plano     | Domínio                                                                                    |
| ------------------ | ------------------------------------------------------------------------------------------ |
| `intent`           | `aggregate`, `ranking` ou `daily`                                                          |
| `metric`           | `revenue`, `orders`, `average_ticket` ou `units`                                           |
| `store_references` | Até seis IDs estáveis, como `a001`, ou nomes permitidos; até 120 caracteres por referência |
| `period`           | Datas ISO `start` e `end`, com fim exclusivo                                               |
| `comparison`       | `previous_period` ou `null`                                                                |
| `grouping`         | `day` ou `null`                                                                            |
| `limit`            | Inteiro de 1 a 20; padrão 5                                                                |

Ranking aceita somente `revenue` ou `units`. Contratos Pydantic usam `extra="forbid"`. O [contrato Python](../backend/src/loja_assistente/analytics/contracts.py) define as combinações válidas e o schema completo.

## Resposta e resultado

Fontes do contrato local: [`contracts.py`](../backend/src/loja_assistente/analytics/contracts.py), [`contracts.py`](../backend/src/loja_assistente/assistant/contracts.py). Conferência documental em **22/09/2026**; regras da implementação, não medição de produção.

| Objeto     | Campos                                                                                                                                                                             |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Resposta   | `id`, `conversation_id`, `question`, `status`, `message`, `mode`, `plan`, `result`, `request_id`, `created_at`                                                                     |
| Resultado  | `intent`, `metric`, `scope`, `period`, `timezone`, `currency`, `unit`, `formula`, `value`, `totals`, `rows`, `coverage`, `comparison`, `evidence`, `dataset_version`, `request_id` |
| Escopo     | Lista de lojas com `id` e `name`                                                                                                                                                   |
| Totais     | `revenue_cents`, `orders`, `units`, `average_ticket_cents`, ou `null`                                                                                                              |
| Linha      | `key`, `label`, `revenue_cents`, `orders`, `units`, `average_ticket_cents`                                                                                                         |
| Cobertura  | `status`, `covered_days`, `expected_days`, `missing` (lista de `store_id` e `date`)                                                                                                |
| Comparação | `period`, `value`, `change_percent`, `message`, ou `null`                                                                                                                          |

Status da resposta: `ready`, `needs_clarification`, `unsupported`, `provider_error` e `no_data`; `plan` e `result` podem ser `null`. Cobertura: `complete`, `partial` ou `absent`. `value` é texto ou `null`, em centavos para receita/ticket e unidades para pedidos/unidades. `change_percent` e `average_ticket_cents` são textos decimais ou `null`.

`rows` de ranking contam pedidos distintos por produto; `evidence` traz agregados diários com o mesmo formato de linha. Em totais, linhas e evidências, `revenue_cents` sai como texto inteiro decimal. No Python permanece `int`; respostas históricas com inteiro JSON são aceitas e serializadas como texto. O OpenAPI também declara string. `Number` no frontend participa somente da geometria dos gráficos; rótulos monetários usam `BigInt` e centavos decimais, sem float monetário.

## Fronteira Python compartilhada

Fontes do contrato local: [`config.py`](../backend/src/loja_assistente/config.py), [`database.py`](../backend/src/loja_assistente/database.py), [`models.py`](../backend/src/loja_assistente/models.py), [`service.py`](../backend/src/loja_assistente/auth/service.py). Conferência documental em **22/09/2026**; regras da implementação, não medição de produção.

- config.py: settings (database_url, reference_date, dataset_version, allowed_origins, session_secret, session_hours, cookie_secure, demo_mode, openai_api_key, openai_model, llm_enabled).
- database.py: Base, engine, SessionLocal, get_db() generator.
- models.py: modelos persistidos e tipados. Conversa: id,tenant_id,user_id,title,created_at,last_plan JSON nullable. AnswerRecord: id,tenant_id,user_id,conversation_id,payload JSON,created_at. Operation: id,tenant_id,user_id,request_id,mode,capability,status,interpretation_ms,query_ms,response_ms,interpreter_version,created_at.
- auth/service.py: Principal dataclass (user_id,tenant_id,name,email,role); get_principal(request,db dependency), require_csrf(request,principal dependency,db dependency); permitted_stores(db,principal) → list[Store]; assert_store_access(db,principal,ids) → list[Store], antes de analytics SQL.
- auth/routes.py: router com /auth.
- analytics/contracts.py: Period, QueryPlan, AnalyticsResult Pydantic (JSON exato acima).
- analytics/service.py: execute_query(db,principal,plan,request_id) → AnalyticsResult; reautoriza antes de dados. InvalidStoreAccess resulta em HTTP 403 genérico; ausência de cobertura retorna result com value null e coverage absent.
- assistant/contracts.py: Interpretation(status,plan,message), AskRequest.
- seed: python -m loja_assistente.seed [--seed 42 --start 2026-05-19 --end 2026-08-17 --version synthetic-v1], sem duplicação. Contas gerente.a@demo.local, supervisor.a@demo.local, gerente.b@demo.local; senha local LojaDemo!2026. Seeds fora de DEMO_MODE=true falham.

Alterações neste contrato devem atualizar consumidores, documentação e testes de integração.

## Detalhes do contrato

Fontes do contrato local: [`queries.py`](../backend/src/loja_assistente/analytics/queries.py), [`service.py`](../backend/src/loja_assistente/conversations/service.py), [`routes.py`](../backend/src/loja_assistente/observability/routes.py). Conferência documental em **22/09/2026**; regras da implementação, não medição de produção.

`totals` é null quando a cobertura é ausente, assim como `value`: ausência não transmite zeros financeiros. `average_ticket_cents` preserva a razão Decimal sem arredondamento intermediário; a apresentação em reais usa HALF_UP. `covered_days` e `expected_days` contam pares loja/data, não apenas datas distintas. Em cobertura parcial, `missing` permite identificar as lojas/dias excluídos.

`response_ms` mede o tempo no serviço até a gravação do registro, incluindo interpretação e consulta; exclui commit, rede e entrega no navegador. Não deve ser somado às demais durações. `/operations` retorna até 100 entradas mais recentes do próprio usuário; total/errors referem-se a essa amostra. Falhas que impedem persistir a operação aparecem apenas nos logs sanitizados, não nessa amostra. Conflito de conversa é `conflict`, contabilizado entre erros; status de acesso recusado é `denied`, sem pergunta ou loja proibida no registro. Campos tokens/cost são null. O proxy preserva `X-Request-ID`, `Cache-Control: no-store` e `X-Content-Type-Options`.

Histórico examina até 50 conversas recentes e oculta aquelas com planos antigos hoje revogados; detalhe retorna até 100 mensagens recentes após reautorizar todos os planos da conversa. Paginação é uma extensão. O último plano é persistido independentemente do limite visual. Consulta concorrente na mesma conversa recebe HTTP 409 e pode ser reenviada após a primeira terminar; o campo de pergunta permanece preenchido diante desse erro.

## Limites de entrada antes do JSON

Fontes do contrato local: [`request_limits.py`](../backend/src/loja_assistente/request_limits.py), [`contracts.py`](../backend/src/loja_assistente/assistant/contracts.py). Conferência documental em **22/09/2026**; regras da implementação, não medição de produção.

Corpos de POST/PUT/PATCH na API têm limite de **16 KiB (16.384 bytes)** antes do decode JSON; o proxy Next aplica o mesmo teto antes de acumular o conteúdo. Content-Length acima do teto é recusado cedo; cabeçalho ausente ou inexato não substitui a contagem dos chunks reais. O limite é inclusivo. Resposta 413 não repete o corpo e preserva request_id, no-store e nosniff.

O proxy inicia um prazo total de **45 s antes de ler o corpo**. O prazo inclui
leitura, fetch e encaminhamento do corpo da resposta; não renova a cada chunk.
Expiração durante a leitura retorna 408 com request_id, no-store e nosniff.
Falha/expiração upstream antes de retornar os cabeçalhos permanece 503. Depois de
iniciada a resposta, o status não pode ser substituído: o stream é interrompido e
o cliente trata JSON incompleto como erro de transporte, sem aceitar null como
resposta bem-sucedida. A resposta continua em streaming, com backpressure.

Abortar a requisição ou cancelar o consumidor encerra a leitura/fetch correspondente.
Timers e listeners são descartados em sucesso, erro e cancelamento. Um hook de
cancelamento que não resolve não impede a liberação do reader ou a resposta de
erro. Isso limita recursos desta requisição no processo, não a quantidade de
conexões simultâneas nem a execução já iniciada no backend. Não há nesta rodada
medição de carga ou garantia contra saturação da infraestrutura.

Pergunta: 1–1.000 caracteres, rejeição de conteúdo só com espaços, trim externo. `store_ids`: até seis referências, sem itens vazios ou maiores que 64 caracteres; duplicatas válidas são removidas sem ampliar escopo. `period` aceita 1–90 dias, datas ISO válidas e fim exclusivo. No formulário, datas vazias/invertidas mantêm a edição, mostram erro associado aos campos e desabilitam envio. A API valida de forma independente. Email aceita 3–254 caracteres, senha 1–200; a senha não é aparada, enquanto email é normalizado para a busca. O login público não revela se a conta existe.
