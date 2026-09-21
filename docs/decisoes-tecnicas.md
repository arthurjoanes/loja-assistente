# Decisões técnicas

## Fluxo

Uma sessão identifica o usuário e sua organização. O servidor oferece ao interpretador somente as lojas permitidas. A pergunta vira um plano Pydantic com capacidades fechadas. O backend resolve as referências e autoriza o plano; a camada SQL revalida as permissões e aplica tenant em todos os joins. Uma consulta já implementada calcula com centavos/Decimal. O mesmo objeto alimenta resposta, tabela, gráfico e painel Cálculo. A conversa persiste o último plano validado, não um estado global compartilhado.

Ordem de leitura no backend: `assistant/service.py → auth/service.py → analytics/service.py → analytics/queries.py → assistant/presentation.py`. `tests/test_security.py` testa que um plano malicioso não chega à consulta, o acesso negado a IDs alheios e a revalidação após revogação. `tests/manual_fixture.py` contém os valores calculados à mão; `evals/cases/manual-v1.json` guarda os resultados esperados versionados.

## Decisões

Por que o modelo só interpreta? A aritmética exige definição estável, dinheiro exato, filtros e rastreabilidade. Uma segunda chamada para redigir números aumenta custo e risco sem melhorar a contabilidade.

Por que autorização não fica no prompt? Saída do modelo e texto do usuário são entradas não confiáveis. Até um plano válido pode pedir loja proibida. A identidade nasce da sessão e as permissões do banco. O mesmo endpoint de analytics aplica a regra sem depender do interpretador.

Como testar os números? A fixture manual contém pedidos com vários itens, desconto total por item, cancelamento, dois instantes na virada UTC/local, receita empatada e tenants com identificadores coincidentes. Os valores esperados foram calculados fora das funções de agregação. O banco real testa joins e COUNT DISTINCT; um mock não cobriria essas propriedades.

Por que não RAG? O problema é selecionar e agregar dados estruturados, com poucas métricas conhecidas. Não há corpus textual a recuperar. Embeddings e SQL livre não melhorariam precisão nem autorização.

Interpretação ou consulta? Compare o plano com o plano esperado. Plano incorreto indica interpretação; plano correto com escopo errado indica autorização; agrupamento/período SQL errado indica consulta; valor/arredondamento errado indica cálculo; objeto correto exibido incorretamente indica apresentação. O relatório separa essas categorias.

Zero ou ausência? Uma tabela de cobertura confirma cada loja-dia. Zero só é apresentado quando a janela tem cobertura. Parcial é explicitado; comparações exigem duas janelas completas. A ausência não é convertida em receita zero.

Qual risco em ticket? Divisão com Decimal não deve ser arredondada em centavos e depois em reais: isso pode mudar o resultado. Preservar a razão até a apresentação evita arredondamento duplo. A soma de tickets diários também não é o ticket do período; a razão deve usar receita/pedidos totais.

Testes do LLM: contratos simulados verificam endpoint, schema, recusa, falhas, tokens/IDs e orçamento antes da rede. A [avaliação Azure](azure-live-results.md), em 21/09/2026, executou o holdout após congelar fontes e casos: 47/48 tentativas aprovadas com LLM, 24/48 com parser e 30/30 consultas estruturadas aplicáveis. Foram 24 perguntas distintas, duas repetições e seis categorias. Das 48 tentativas do sistema com LLM, 42 chamaram o modelo e seis foram resolvidas por guardas locais. A aprovação atende aos limiares definidos antes; não transforma repetições em exemplos independentes nem mede produtividade de usuários.

Qual falha permaneceu? Em `final-bf-04`, repetição 2, o modelo pediu esclarecimento para indicar dias não carregados, embora o backend já devolva cobertura automaticamente. O caso passou na primeira repetição. A falha não executou consulta analítica nem devolveu plano ou número incorreto. Houve um esclarecimento desnecessário em 30 tentativas executáveis; nenhuma violação de escopo, aceitação insegura ou divergência financeira. O prompt não foi ajustado e a avaliação não foi repetida após abrir o holdout.

O que mudou para funcionar no Azure? O adaptador usa Responses com JSON Schema strict no subconjunto aceito pelo Azure. O schema enviado omite constraints incompatíveis; o modelo Pydantic de domínio permanece intacto e valida a saída antes de autorização e SQL. A configuração avaliada foi `gpt-5.6-luna`, versão `2026-07-09`, GlobalStandard, recurso East US 2, com reasoning effort `none`.

O que torna o problema difícil? Não é adicionar uma caixa de chat. “Somente em dinheiro” pode desaparecer e devolver um total correto para a pergunta errada. Uma loja do plano pode ser válida no schema e proibida para a sessão. A correção depende de intenção, permissões atuais, datas, cobertura e aritmética ao mesmo tempo. A [matriz de critérios](problem-solution.md) mostra o que foi exercitado e o que poderia refutar a hipótese de valor.

Como controlar custo e registro? Reserva persistente antes de enviar, tentativas limitadas sem retries, uso desconhecido conservando reserva e preço documentado separado da fatura. Logs não substituem os campos esperados. Falhas da avaliação final não podem ser apagadas; ajustar com base nelas contamina o holdout e exige uma nova amostra explícita.

Smoke, desenvolvimento e final somaram 55 chamadas, 48.788 tokens e US$ 0,01550395 estimados de forma conservadora. O cálculo usa entrada a US$ 0,25/milhão e saída a US$ 1,20/milhão. O teto de US$ 15 valia só para essa avaliação; não configura quota Azure nem limita globalmente chamadas feitas pela interface. Com LLM habilitado, selecionar esse modo permite uso cobrado fora desse ledger.

## Caminho para uso real

Separar importação/validação de dados reais de consultas; definir reconciliação financeira, fuso e tratamento de reembolsos; substituir contas fictícias por identidade corporativa; aplicar HTTPS, proteção contra força bruta e rotação de segredos; revisar role do banco e considerar RLS com testes da role efetiva; definir retenção/auditoria de perguntas; ampliar avaliações com novas amostras representativas e monitorar erros. A aprovação técnica usa dados sintéticos e transporte ASGI com PostgreSQL real; não valida utilidade com usuários, latência do navegador nem produção. Só adicionar cache ou serviços separados após medir necessidade.
