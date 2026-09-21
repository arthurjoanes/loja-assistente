# Contrato HTTP e integração interna — revisão 2

Todos os caminhos possuem prefixo /api; Next faz proxy para backend. Erros HTTP usam {detail: string}. Sessão: cookie la_session. POST exige Origin permitido; exceto login exige X-CSRF-Token. JSON usa snake_case.

- POST /auth/login {email,password} → mesmo objeto de GET /auth/me, com cookie.
- GET /auth/me → {user:{id,name,email,role,organization:{id,name},stores:[{id,name}]},csrf_token,reference_date,dataset_version,llm_available}.
- POST /auth/logout → {ok:true}.
- GET /conversations → [{id,title,created_at}].
- POST /conversations {} → {id,title,created_at}.
- GET /conversations/{id} → {id,title,created_at,messages:[Answer]}.
- POST /assistant/query {question,conversation_id:null|string,mode:demo|llm,store_ids:[],period:null|{start,end}} → Answer.
- POST /analytics/query Plan → Result (CSRF obrigatório; mesma autorização).
- GET /answers/{id} → Answer; GET /answers/{id}/evidence → Result.
- GET /operations → {entries:[{request_id,mode,capability,status,interpretation_ms,query_ms,response_ms,created_at,interpreter_version}],total,errors,tokens:null,cost:null}.
- GET /health → {status:ok}; readiness verifica SELECT 1.

Plan={intent:aggregate|ranking|daily,metric:revenue|orders|average_ticket|units,store_references:string[],period:{start:ISOdate,end:ISOdate},comparison:previous_period|null,grouping:day|null,limit:int}. period.end é exclusivo. A referência pode ser ID estável (a001) ou nome permitido. Ranking só aceita revenue ou units. Contratos Pydantic com extra=forbid.

Answer={id,conversation_id,question,status:ready|needs_clarification|unsupported|provider_error|no_data,message,mode,plan:Plan|null,result:Result|null,request_id,created_at}.

Result={intent,metric,scope:[{id,name}],period:{start,end},timezone,currency,unit,formula,value:string|null,totals:null|{revenue_cents:string,orders:int,units:int,average_ticket_cents:string|null},rows:[{key,label,revenue_cents,orders,units,average_ticket_cents}],coverage:{status:complete|partial|absent,covered_days:int,expected_days:int,missing:[{store_id,date}]},comparison:null|{period:{start,end},value:string|null,change_percent:string|null,message:string},evidence:[{key,label,revenue_cents,orders,units,average_ticket_cents}],dataset_version,request_id}. value está em centavos para revenue/average_ticket e unidades para orders/units. rows de ranking têm orders distintos por produto; evidências são agregados diários. Em todos os totais, linhas e evidências, `revenue_cents` é texto inteiro decimal. No Python permanece `int`; respostas históricas com JSON inteiro são aceitas e serializadas como texto ao sair. O contrato de saída/OpenAPI também declara string. Conversão para `Number` no frontend só participa da geometria dos gráficos; rótulos monetários usam BigInt e centavos decimais. Valor nunca float monetário.

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

Histórico examina até 50 conversas recentes e oculta aquelas com planos antigos hoje revogados; detalhe retorna até 100 mensagens recentes após reautorizar todos os planos da conversa. Paginação é uma extensão. O último plano é persistido independentemente do limite visual. Consulta concorrente na mesma conversa recebe HTTP 409 e pode ser reenviada após a primeira terminar; o campo de pergunta permanece preenchido diante desse erro.

## Limites de entrada antes do JSON

Corpos de POST/PUT/PATCH na API têm limite de **16 KiB (16.384 bytes)** antes do decode JSON; o proxy Next aplica o mesmo teto antes de acumular o conteúdo. Content-Length acima do teto é recusado cedo; cabeçalho ausente ou inexato não substitui a contagem dos chunks reais. O limite é inclusivo. Resposta 413 não repete o corpo e preserva request_id, no-store e nosniff. Isso limita o corpo acumulado pela aplicação, não constitui proteção completa contra conexões lentas ou força bruta.

Pergunta: 1–1.000 caracteres, rejeição de conteúdo só com espaços, trim externo. `store_ids`: até seis referências, sem itens vazios ou maiores que 64 caracteres; duplicatas válidas são removidas sem ampliar escopo. `period` aceita 1–90 dias, datas ISO válidas e fim exclusivo. No formulário, datas vazias/invertidas mantêm a edição, mostram erro associado aos campos e desabilitam envio. A API valida de forma independente. Email aceita 3–254 caracteres, senha 1–200; a senha não é aparada, enquanto email é normalizado para a busca. O login público não revela se a conta existe.

