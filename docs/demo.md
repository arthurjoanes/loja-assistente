# Roteiro da demonstração

## Problema e prova em 5–8 minutos

1. **1 min:** abra [o baseline](evidence/problem-review/parser-before.json): acrescentar “eu” derrubava a pergunta. Explique que decorar frases não demonstra interpretação natural. Um dashboard com filtros é a alternativa simples.
2. **2 min:** na aplicação, compare “Quanto vendi ontem?”, “Quanto eu vendi ontem?” e “Me mostra o faturamento de ontem”. Confira loja, datas, dinheiro e Cálculo. Identifique o modo selecionado: **Demo** usa o parser offline; **LLM** usa o deployment Azure configurado. A seleção LLM permite chamadas cobradas.
3. **1 min:** peça “Só queria saber quanto vendi ontem somente em dinheiro”. Nenhum total geral deve surgir. Mostre a regressão que observa ausência de SQL e a autorização de um plano malicioso em `backend/tests/test_security.py`.
4. **2 min:** abra os [resultados Azure da rodada r1](azure-live-results.md): o sistema com LLM passou em **47/48 tentativas**, o parser em **24/48**, e a consulta estruturada em **30/30 tentativas aplicáveis**. São **24 perguntas distintas repetidas duas vezes**, com 42 chamadas reais ao modelo e seis decisões locais; a baseline estruturada cobre os 15 casos com plano, também repetidos duas vezes. Mostre a falha `final-bf-04`, repetição 2: esclarecimento desnecessário sobre dias sem cobertura, sem consulta ou número incorreto. A aprovação segue limiares definidos antes da rodada; não significa acerto perfeito.
5. **1 min:** siga `interpretation.py → service.py → analytics/queries.py`. Explique que não há SQL livre nem conta feita pelo modelo; um JSON válido ainda pode interpretar errado. Mostre um compromisso: capacidades fechadas reduzem risco, mas limitam perguntas. Utilidade com usuários continua pendente.

O roteiro detalhado abaixo cobre as capacidades analíticas. Para ensaios repetidos use o modo Demo e o ambiente E2E isolado; consultas na interface ficam no histórico pessoal. O teto autorizado de **US$ 15** controla somente a rodada do avaliador: não é uma quota Azure nem um limite global de gasto da interface.

Inicie pelo README. Os indicadores consultam PostgreSQL; perguntas fora das capacidades não executam consultas analíticas. A referência analítica visível é 17/08/2026.

1. Entre com `gerente.a@demo.local` / `LojaDemo!2026`. Pergunte **Quanto vendi ontem?**. O resultado deve usar 16/08/2026 e loja a001. Abra **Cálculo** e confira fórmula, totais, cobertura, versão e request_id.
2. Pergunte **Quais os 5 produtos com maior receita nos últimos 7 dias?**. Alterne gráfico/tabela e confira o mesmo ranking. Desempates seguem o ID do produto.
3. Pergunte **Compare a receita dos últimos 7 dias com o período anterior**. A janela atual é [10/08,17/08), e a anterior [03/08,10/08). Em seguida **E nos sete dias anteriores?** usa a mesma conversa e desloca o período para [03/08,10/08).
4. Em **Atendimentos**, confira request_id, modo, status e duração. A lista contém até 100 consultas da conta; esse painel não exibe tokens nem custo. A medição por chamada pertence ao avaliador autorizado.
5. Saia e entre com `gerente.b@demo.local`. Faça **Quanto vendi ontem?**. O escopo agora é Brisa Casa / b001, e o valor difere. O histórico A não aparece. As jornadas E2E também tentam abrir diretamente os IDs de resposta/evidência A e conferem 404 e ausência de dados.
6. De volta ao gerente A, **Faturamento na loja b001 ontem** deve ser bloqueado com 403 no backend. **Qual foi o lucro ontem?** explica a capacidade ausente. **Receita em 2025-01-01** informa período não carregado com `value=null`, sem transformar ausência em zero.
7. Como supervisor A, selecione Jardins e “últimos 7 dias” no filtro; pergunte **Quanto vendi ontem?**. A loja permanece Jardins e o período efetivo muda para ontem. Abra nova análise e use **Evolução diária da receita nos últimos 7 dias**.
8. Abra [o relatório de avaliações](../evals/reports/latest.md): distingue perguntas demo, consultas estruturadas e stub de interpretador malicioso. Os valores financeiros vêm da fixture manual, independente da massa ilustrada na interface.

Automação HTTP do roteiro pelo proxy Next.js, para conferir frontend e API em execução (execute na raiz do projeto):

```powershell
docker compose run --rm --volume "${PWD}/docs:/app/docs" backend python /app/scripts/demo_check.py
```

O cliente usa `http://frontend:3102` dentro da rede Docker; no navegador, o endereço correspondente é `http://localhost:3102`. O resultado fica em [demo-results.json](demo-results.json), com horário real e endereço utilizado. As screenshots da pasta `screenshots` vêm do Chromium executando a aplicação real. [verification.md](verification.md) registra quais comandos e jornadas foram executados.

A integração configurada usa **gpt-5.6-luna, versão 2026-07-09, GlobalStandard, recurso East US 2, reasoning effort `none`**. Com LLM habilitado na aplicação, selecione esse modo para consultar o provedor; Demo continua disponível sem chave. O protocolo de [avaliação delimitada](live-evaluation.md) é separado do uso pela interface.

Smoke, desenvolvimento e final r1 somaram **55 chamadas e 48.788 tokens**, com estimativa conservadora de **US$ 0,01550395**, usando US$ 0,25 por milhão de entrada e US$ 1,20 por milhão de saída. A estimativa não é fatura. O [relatório consolidado](azure-live-results.md) preserva a falha, a origem dos preços e os resultados originais; não houve ajuste de prompt nem repetição após examinar o holdout. Utilidade com usuários e qualidade em produção ainda não foram avaliadas.
