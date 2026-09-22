# Integração OpenAI / Azure

Um único adaptador usa SDK OpenAI 3.16.2 e `responses.with_raw_response.create`, com JSON Schema em `text.format` e `strict: true`. A saída é validada por `Interpretation.model_validate_json`. O servidor autoriza e calcula; o modelo recebe só pergunta, referência analítica, lojas permitidas, filtros e último plano validado. Não recebe vendas, sessão ou histórico textual completo.

`OPENAI_BASE_URL` aceita `https://api.openai.com/v1/` ou `https://SEU-RECURSO.openai.azure.com/openai/v1/` (também o domínio Azure `services.ai.azure.com`). `OPENAI_MODEL` contém o snapshot no OpenAI ou **nome do deployment** no Azure. Configure `OPENAI_API_KEY` apenas no `.env` ignorado. Endpoint de projeto `/api/projects/...` não é endpoint de inferência. Suporte de Responses/saída estruturada depende do deployment real.

## Ativação e orçamento

`LLM_ENABLED=false` é o padrão. Com o provedor configurado e o LLM habilitado na aplicação, é possível selecionar LLM na interface, o que permite chamadas cobradas. O [runner de avaliação com autorização e teto](live-evaluation.md) ativa seu próprio processo isolado e mantém um ledger específico da execução. O teto de US$ 15 usado na avaliação não é quota Azure nem limite global da interface. Nenhum recurso Azure é criado pelo projeto.

O caminho LLM da API exige ainda uma [conta de orçamento por organização](provider-budget.md), criada pelo CLI local após a migração 0003. Não há saldo concedido automaticamente. Reserva e despacho são persistidos antes do SDK; uso desconhecido mantém saldo comprometido. O controle local não abrange outras aplicações que compartilhem a credencial nem garante um teto monetário do recurso.

## Contrato e limites do adaptador

Versão `openai-structured-v5`: saída até 1.000 tokens, `store=false`, timeout de comunicação de 12 s e zero retries. Timeout de comunicação não é deadline total. Schema inválido, recusa, incompleta, quota e conexão têm categorias próprias no registro; a UI apresenta erro do provedor sem resposta silenciosa do parser. Campos extras, como SQL/tenant/usuário, são rejeitados.

O schema de transporte usa o subconjunto strict do Azure: retira `default`, `format` e constraints de tamanho/limites que o provedor não aceita, exige todas as propriedades e define `additionalProperties: false`. Essa adaptação não remove validações do domínio: o contrato Pydantic continua rejeitando limites, datas e combinações inválidas antes de autorização ou consulta. O prompt e o contrato de negócio permaneceram congelados durante a avaliação.

A guarda local recusa dimensões explicitamente ausentes do contrato. Prefixos de saudação/cortesia não contam como filtros; qualificadores posteriores continuam sendo verificados. O prompt pede esclarecimento para múltiplas métricas e filtros não representáveis. Isso reduz algumas falhas previsíveis, mas schema válido e prompt não garantem compreensão nem autorização.

O avaliador registra uma lista explícita de metadata: IDs local/provedor, versão retornada quando disponível, hashes de prompt/schema, status, duração, tentativas e tokens informados. O corpo bruto é usado apenas para extrair esse uso antes do parsing e não é gravado. Não há raciocínio interno, headers, cookies ou chave no relatório. Custo estimado usa preço e data conferidos; cobrança efetiva não é inventada. A tela de atendimentos continua mostrando apenas as métricas que persiste, sem custo fictício.

## Avaliação histórica

A [avaliação Azure de 21/09/2026](azure-live-results.md) recebeu `live_final_approved`, com 47/48 tentativas aprovadas no modo LLM, 24/48 no parser e 30/30 na baseline estruturada aplicável. O deployment foi gpt-5.6-luna, versão 2026-07-09, GlobalStandard, recurso East US 2, com reasoning effort `none`. Foram 24 perguntas distintas repetidas duas vezes; 42 tentativas finais fizeram chamada real e seis passaram pelas guardas locais.

A única falha LLM foi `final-bf-04`, repetição 2: esclarecimento desnecessário ao pedir os dias não carregados, informação que o backend fornece na cobertura. Não houve plano, resultado financeiro nem consulta analítica nessa tentativa. A categoria financeira passou em 7/8 tentativas, acima do limiar prévio de 80%; a aprovação geral exige ao menos 90%, sem falhas críticas. A falha foi preservada; não houve ajuste de prompt ou repetição depois de examinar o holdout.

Smoke, desenvolvimento e final somaram 55 chamadas e 48.788 tokens, com estimativa conservadora de US$ 0,01550395. Para a reserva e a estimativa, a entrada foi avaliada a US$ 0,25/milhão (maior tarifa de entrada entre os medidores normais e de escrita em cache conferidos), e a saída a US$ 1,20/milhão. Não é fatura nem medição do gasto total do recurso. A avaliação verifica interpretação, autorização e cálculo em fixture sintética, com ASGI e PostgreSQL real; utilidade com usuários, latência do navegador e produção ficam fora dela. [Protocolo e comandos](live-evaluation.md), [problema e critérios](problem-solution.md).

Referências: [Azure endpoints](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/endpoints), [Azure Structured Outputs](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/structured-outputs), [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

## Código e evidências relacionados

[lock](../backend/uv.lock) · [adaptador](../backend/src/loja_assistente/assistant/interpreters/openai_adapter.py) · [configuração](../backend/src/loja_assistente/config.py).
