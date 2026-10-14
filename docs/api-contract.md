# Contrato HTTP e integração interna

Todos os caminhos têm prefixo `/api`, e Next.js encaminha as requisições ao backend. Erros HTTP usam `detail` textual. A sessão usa o cookie `la_session`. POST exige `Origin` permitido; depois do login também exige `X-CSRF-Token`. JSON usa `snake_case`.

## Rotas

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
| `GET /health`                | Sem entrada                                     | `status: "ok"`; prontidão verifica `SELECT 1`                               |

O usuário de `/auth/me` contém `id`, `name`, `email`, `role`, `organization` (`id`, `name`) e `stores` (lista de `id`, `name`). Cada entrada operacional contém `request_id`, `mode`, `capability`, `status`, `interpretation_ms`, `query_ms`, `response_ms`, `created_at` e `interpreter_version`.

## Pergunta e plano

| Entrada da pergunta | Interpretação                        |
| ------------------- | ------------------------------------ |
| `question`          | Texto da pergunta                    |
| `conversation_id`   | ID textual ou `null`                 |
| `mode`              | `demo` ou `llm`                      |
| `store_ids`         | Lista de IDs de lojas                |
| `period`            | `null` ou objeto com `start` e `end` |
| `client_request_id` | Identificador da intenção, de 1 a 64 caracteres; a interface envia UUID |

Com `client_request_id`, a admissão é gravada antes da interpretação, com unicidade por tenant/usuário e fingerprint do pedido. Repetição idêntica recupera a resposta existente; conteúdo diferente retorna 409. `GET /assistant/requests/{client_request_id}` recupera a resposta com autorização atual, retorna 404 sem admissão e 409 enquanto a execução não tiver publicação confirmada. Uma execução incerta nunca dispara outra chamada ao provedor ao repetir a chave. O vínculo da resposta com a intenção é publicado na mesma transação da resposta. Clientes antigos sem esse campo continuam aceitos, sem garantia de repetição segura.

Após falha de transporte, a interface conserva pergunta e intenção e bloqueia outro envio e a abertura de outra conversa até **Recarregar estado atual**. Consultar a lista de favoritos não remove esse bloqueio; executar um favorito ou abrir seu cálculo também exige resolver a intenção. Se a recuperação retornar 404, reenvia o corpo original com a mesma chave e confirma esse envio; se retornar 409, mantém a incerteza. **Nova análise** abandona explicitamente a recuperação local e permite preparar outra intenção, sem cancelar nem negar uma execução já iniciada no servidor. Sair da conta limpa a intenção local, e respostas tardias da sessão anterior são descartadas. Admissões sem resposta após falha do processo devem ser investigadas; não são expiradas automaticamente como se nenhuma chamada tivesse ocorrido. A migração `0006` deve ser aplicada antes de iniciar a versão nova.

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

`totals` é null quando a cobertura é ausente, assim como `value`: ausência não transmite zeros financeiros. `average_ticket_cents` preserva a razão Decimal sem arredondamento intermediário; a apresentação em reais usa HALF_UP. `covered_days` e `expected_days` contam pares loja/data, não apenas datas distintas. Em cobertura parcial, `missing` permite identificar as lojas/dias excluídos.

`response_ms` mede o tempo no serviço até a gravação do registro, incluindo interpretação e consulta; exclui commit, rede e entrega no navegador. Não deve ser somado às demais durações. `/operations` retorna até 100 entradas mais recentes do próprio usuário; total/errors referem-se a essa amostra. Falhas que impedem persistir a operação aparecem apenas nos logs sanitizados, não nessa amostra. Conflito de conversa é `conflict`, contabilizado entre erros; status de acesso recusado é `denied`, sem pergunta ou loja proibida no registro. Campos tokens/cost são null. O proxy preserva `X-Request-ID`, `Cache-Control: no-store` e `X-Content-Type-Options`.

`GET /conversations/page?cursor=` retorna `{items,next_cursor,has_more}`, com até 50 conversas autorizadas por página, em ordem de criação/ID decrescente. Conversas revogadas são excluídas antes de completar a página. O endpoint antigo `/conversations` conserva a lista simples da primeira página. O detalhe retorna as 100 respostas mais recentes e `messages_next_cursor`; `GET /conversations/{id}/messages?cursor=` entrega anteriores no mesmo envelope paginado, com `items` em ordem cronológica para leitura. Cursors são assinados e vinculados a tenant, usuário e escopo; acesso atual é revalidado em cada página, inclusive permissões de planos e esclarecimentos anteriores. O último plano continua independente da página em leitura.

Histórico e favoritos carregam de forma independente. Uma falha em favoritos não impede restaurar o esclarecimento pendente; falha do histórico tem mensagem e recarga próprias. 401/403 continuam invalidando o estado protegido. Uma intenção de consulta já admitida sem resposta confirmada deve ser recuperada pela mesma chave; iniciar outra é uma execução explícita.

## Limites de entrada antes do JSON

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

Pergunta: 1 a 1.000 caracteres, rejeição de conteúdo só com espaços, trim externo. `store_ids`: até seis referências, sem itens vazios ou maiores que 64 caracteres; duplicatas válidas são removidas sem ampliar escopo. `period` aceita 1 a 90 dias, datas ISO válidas e fim exclusivo. No formulário, datas vazias/invertidas mantêm a edição, mostram erro associado aos campos e desabilitam envio. A API valida de forma independente. Email aceita 3 a 254 caracteres, senha 1 a 200; a senha não é aparada, enquanto email é normalizado para a busca. O login público não revela se a conta existe.

## Admissão do login

`POST /auth/login` retorna 429 e `Retry-After` em segundos ao atingir cinco tentativas malsucedidas ou em andamento por conta normalizada, ou trinta por origem. A janela dura 60 segundos desde a primeira reserva. O PostgreSQL registra a admissão antes do Argon2 e conserva o contador após 401 ou rollback. Um login concluído libera apenas sua própria reserva. A conta compartilha a cota entre origens; clientes do proxy Next.js compartilham a cota da conexão do proxy. A [política de segurança](security.md) descreve a migração e os limites desse controle.

## Favoritos e esclarecimentos

Todas as mutações abaixo usam POST, com sessão, Origin permitido e CSRF. O proxy Next continua encaminhando GET/POST por toda a cadeia. Identidade, tenant, planos e opções autorizadas vêm do servidor.

| Método e caminho | Entrada | Retorno |
| --- | --- | --- |
| `GET /favorites` | Sessão | Até 50 favoritos autorizados, lista sem wrapper |
| `GET /favorites/{id}` | ID | Favorito autorizado |
| `POST /favorites` | `answer_id`, `name` | Favorito; 200 também em criação duplicada |
| `POST /favorites/{id}/rename` | `name`, `revision` | Favorito com nova revisão |
| `POST /favorites/{id}/delete` | `revision` | 204 sem corpo |
| `POST /favorites/{id}/run` | `revision` | `Answer` novo, persistido com request_id novo |
| `POST /conversations/{id}/clarification/respond` | `pending_id`, `revision`, `choice_id` | `Answer`, com resultado ou próxima pendência |
| `POST /conversations/{id}/clarification/cancel` | `pending_id`, `revision` | Pendência com status `cancelled` |

Favorito: `id`, `name`, `plan`, `schema_version=1`, `source_answer_id`, `created_at`, `updated_at`, `revision`. Nome aceita até 120 caracteres após trim e não pode ser vazio. O plano é copiado de uma resposta válida do próprio usuário; planos/tenant enviados pelo cliente são rejeitados. Datas são absolutas. Salvar novamente a mesma resposta retorna o favorito existente, sem renomear. Renomear, excluir e executar exigem revisão atual e lock `NOWAIT`. Executar também aumenta revisão. 409 exige recarregar; depois de timeout não há retry automático de execução. Histórico e evidência de origem permanecem imutáveis.

Um favorito revogado é omitido da listagem; detalhe e ações retornam 403 sem nome/plano. IDs alheios retornam 404. Schema ou plano persistido inválido não é executado. Salvar, listar e reexecutar reconsultam permissões; favoritos não são transferidos entre contas.

`Answer`, resumo e detalhe da conversa acrescentam `pending_clarification` opcional, com padrão null para persistência antiga. `PartialPlan` contém `intent`, `metric`, `store_ids`, `period` nullable, `comparison`, `grouping` e `limit`. `PendingClarification` contém `id`, `revision`, `status` (`pending`, `resolved`, `cancelled`, `expired`), `original_question`, `partial_plan`, `missing_field` (`period` ou `store`), `choices`, `created_at`, `expires_at`, `schema_version=1`, `mode` e `reference_date`. Cada escolha contém `id`, `label`, `period` nullable e `store_ids` nullable.

Escolhas de período: ontem, últimos 7 dias e últimos 30 dias; o servidor resolve datas pela referência analítica capturada, com fim exclusivo. Escolhas de loja contêm até seis IDs autorizados, com nomes e IDs para distinguir duplicatas. A pendência expira em 30 minutos pelo relógio real. Resposta a pendência terminal, substituída ou com revisão antiga recebe 409. Refresh recupera o estado pelo detalhe da conversa. A conclusão reautoriza cada loja e valida QueryPlan antes de executar sem interpretador/LLM. Sem seleção, todas as lojas permitidas continuam sendo o padrão. Filtro fora do domínio não produz opções executáveis.

`Answer.clarification_response` opcional registra `pending_id`, `revision`, `choice_id` e `label` da escolha recebida. As respostas antigas permanecem aceitas sem esse campo.

Fontes: [contratos favoritos](../backend/src/loja_assistente/favorites/contracts.py), [contratos esclarecimento](../backend/src/loja_assistente/clarifications/contracts.py), [TypeScript](../frontend/src/lib/contracts.ts).

## Código e evidências relacionados

| Tema                             | Implementação e critérios                                                                                                                                                                                                                                                                                                   |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Rotas                            | [`auth/routes.py`](../backend/src/loja_assistente/auth/routes.py) · [`assistant/routes.py`](../backend/src/loja_assistente/assistant/routes.py) · [`conversations/routes.py`](../backend/src/loja_assistente/conversations/routes.py) · [`observability/routes.py`](../backend/src/loja_assistente/observability/routes.py) |
| Pergunta e plano                 | [`assistant/contracts.py`](../backend/src/loja_assistente/assistant/contracts.py)                                                                                                                                                                                                                                           |
| Fronteira Python compartilhada   | [`config.py`](../backend/src/loja_assistente/config.py) · [`database.py`](../backend/src/loja_assistente/database.py) · [`models.py`](../backend/src/loja_assistente/models.py) · [`auth/service.py`](../backend/src/loja_assistente/auth/service.py)                                                                       |
| Detalhes do contrato             | [`queries.py`](../backend/src/loja_assistente/analytics/queries.py) · [`conversations/service.py`](../backend/src/loja_assistente/conversations/service.py)                                                                                                                                                                 |
| Limites de entrada antes do JSON | [`request_limits.py`](../backend/src/loja_assistente/request_limits.py)                                                                                                                                                                                                                                                     |
