# Contrato de dados

Dados gerados localmente com `random.Random(seed)`. A base inclui IDs repetidos entre tenants, dias sem carga, dias sem vendas, cancelamentos, descontos e texto hostil em nomes de produtos.

## Massa padrão

`python -m loja_assistente.seed --seed 42 --start 2026-05-19 --end 2026-08-17 --version synthetic-v1` gera 90 dias comerciais, com início incluído e fim excluído. A referência analítica é 17/08/2026. O manifesto efetivamente gerado está em `data/manifests/synthetic-v1.json`; ele registra configuração, contagens e SHA-256 do conteúdo de domínio em JSON canônico. Hashes Argon2 e instantes de sessões ficam fora desse fingerprint, pois usam aleatoriedade e relógio reais.

Aurora Casa (`org_a`) e Brisa Casa (`org_b`) têm as lojas Centro, Jardins e Norte e 20 produtos cada. Referências `PROD-001`, `LOJA-001` e `PED-000001` se repetem entre tenants. IDs de produtos e pedidos também se repetem; a identidade inclui o tenant.

A execução padrão verificada gerou **6.316 pedidos**, **15.683 itens** e **538 pares loja/data carregados**, entre 540 possíveis. O plano da consulta diária real e seu contexto local estão em [query-plan.md](query-plan.md).

| Entidade | Campos relevantes | Invariantes |
|---|---|---|
| Organização | id, name | Identidade do tenant |
| Loja | tenant_id, id, external_id, name | Chave composta; origem única dentro do tenant |
| Usuário | id, tenant_id, name, email, role, password_hash | E-mail único; senha Argon2; tenant derivado da sessão |
| Permissão | tenant_id, user_id, store_id | FKs compostas impedem vincular usuário/loja de tenants distintos |
| Produto | tenant_id, id, external_id, name | Nome não é instrução; precisa de escape na apresentação |
| Pedido | tenant_id, id, store_id, external_id, occurred_at, status | Instante UTC; status `completed` ou `cancelled` |
| Item | tenant_id, id, order_id, product_id, quantity, unit_price_cents, discount_cents | Quantidade positiva, centavos inteiros, desconto entre zero e subtotal |
| Cobertura | tenant_id, store_id, date | Uma linha indica dia comercial carregado, mesmo sem venda |
| Dataset | version, seed, start_date, end_date, manifest | Configuração e integridade da massa instalada |

Sessões guardam somente digest HMAC do cookie opaco, token CSRF e expiração real. Conversas pertencem ao par tenant/usuário; respostas têm FK composta para sua conversa; operações pertencem ao mesmo escopo. Os registros não usam o relógio analítico para expirar sessões ou medir duração.

## Cobertura e dinheiro

Eventos são `TIMESTAMPTZ` UTC. Os filtros comerciais em America/Sao_Paulo são convertidos antes da consulta; o agrupamento diário usa o mesmo fuso. As definições financeiras estão somente em [metrics.md](metrics.md).

Todos os itens da massa possuem quantidade, preço unitário em centavos e desconto total do item. Pedidos cancelados são excluídos integralmente. A moeda única é BRL. Nenhuma coluna modela imposto, reembolso parcial, lucro, estoque, cliente ou causa de uma variação.

O gerador produz volume variável por loja, concentração em itens populares, reforço de vendas de sexta a domingo, descontos e aproximadamente 7% de cancelamentos. Alguns dias carregados não têm vendas. Nas lojas Norte, um dia não é carregado deliberadamente; nenhuma venda é gerada nesse dia. A consulta também associa os pedidos à cobertura, portanto uma linha de venda acidental num dia não carregado não entra nos valores.

Cobertura conta pares loja/data. Completa permite comparação. Parcial mostra somente os dias carregados e lista os pares ausentes; a comparação é recusada. Ausente retorna `value=null`, `totals=null`, série e `evidence` vazios. Uma janela coberta sem pedidos tem receita/pedidos/unidades zero e ticket indisponível.

## Repetição e limites

Seed exige `DEMO_MODE=true`, usa uma transação PostgreSQL e trava consultiva local para serializar execuções concorrentes. Com o mesmo seed/período/versão e contagens íntegras, retorna o manifesto existente, sem duplicar registros ou redefinir senhas. Outra configuração ou banco com dados sem manifesto causa falha explícita; nenhum truncamento ocorre automaticamente. Não há reset destrutivo automático: trocar a massa exige uma operação explícita sobre o volume exclusivo deste projeto, preservando fontes e documentação.

O SHA-256 identifica a massa gerada. Repetir o seed confere contagens, sem recalcular o checksum das linhas.

A fixture de valores manuais é independente da massa e do algoritmo financeiro. Veja [manual-fixture.md](manual-fixture.md) e `backend/tests/manual_fixture.py`. Ela é executada somente em PostgreSQL dedicado com nome terminado em `_test`.
