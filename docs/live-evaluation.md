# Avaliação de interpretação

Estado: **avaliação Azure aprovada pelos critérios prévios**, com 47/48 resultados corretos no caminho modelo + backend. [Resultado, evidências, custo e falha preservada](azure-live-results.md). O restante deste documento define o protocolo de reprodução; a autorização usada já teve suas três etapas executadas e não deve ser reutilizada para repetir rodadas.

## O que comparar

O avaliador usa o mesmo endpoint FastAPI, sessão, regras e PostgreSQL da aplicação, com transporte ASGI e banco dedicado. A fixture manual independente define o esperado. Parser, modelo e consulta estruturada têm denominadores separados. Consulta estruturada serve como baseline de correção; não mede tempo de uma pessoa preenchendo filtros. A prova do proxy/navegador é uma jornada separada, no Compose E2E.

`development-v1.json` tem 12 casos conhecidos. Um revisor prepara 24 casos finais em seis categorias sem mostrar suas frases ao implementador. `freeze.json` fixa hashes das fontes e casos antes de abrir o holdout. Cada caso final tem duas repetições. Uma rodada completa admite um smoke, 12 casos de desenvolvimento e 48 tentativas finais: teto de 61 tentativas, zero retries e nenhum modelo juiz. Guardas locais podem evitar algumas chamadas, mas seus casos permanecem na avaliação.

Planos equivalentes têm mesma intenção, métrica, lojas resolvidas, janela, agrupamento e comparação. Ordem de lojas não importa; limite só importa em ranking. Mensagem livre não é usada como oráculo. Os resultados usam valores literais independentes, e a evidência persistida deve ser idêntica ao resultado retornado. Um listener registra a quantidade de consultas analíticas para impedir que uma recusa esconda acesso.

## Configuração local

No `.env` ignorado, configure `OPENAI_BASE_URL=https://SEU-RECURSO.openai.azure.com/openai/v1/`, `OPENAI_MODEL=NOME-DO-DEPLOYMENT` e `OPENAI_API_KEY`. Mantenha `LLM_ENABLED=false`: o avaliador ativa seu próprio processo apenas depois da autorização. Não cole a chave em chats, logs ou relatórios. Não use endpoint de projeto `/api/projects/...`; o deployment precisa oferecer Responses com saída estruturada. Configure OPENAI_REASONING_EFFORT=none para reproduzir o perfil Luna avaliado. O mesmo SDK OpenAI é usado, com timeout de comunicação de 12 s e zero retries; isso não é um deadline total de 12 s.

Antes de live, conferir modelo/versão, região, quotas e preço com fonte/data. Não criar recurso nem aumentar quota. A oferta de uma chave não substitui autorização de gasto.

Crie `.runtime/live-authorization.json` **somente após autorizar a rodada** com campos:

```json
{
  "authorized": false,
  "approval_id": "identificador-da-autorizacao-do-usuario",
  "endpoint": "https://SEU-RECURSO.openai.azure.com/openai/v1/",
  "deployment": "NOME-DO-DEPLOYMENT",
  "stages": ["smoke", "development", "final"],
  "expires_at": "SUBSTITUIR-POR-DATA-UTC-AUTORIZADA",
  "max_calls": 61,
  "max_input_tokens": 1220000,
  "max_output_tokens": 61000,
  "input_usd_per_million": "PREENCHER-PRECO-CONFERIDO",
  "output_usd_per_million": "PREENCHER-PRECO-CONFERIDO",
  "price_source": "PREENCHER-URL-HTTPS-OFICIAL",
  "price_checked_at": "PREENCHER-DATA",
  "max_estimated_usd": "PREENCHER-TETO-AUTORIZADO"
}
```

O exemplo não é uma autorização e não funciona sem preencher valores. Os tetos de tokens são reservas conservadoras, não expectativa de consumo: bytes UTF-8 de prompt/contexto/schema mais margem de protocolo, até 1.000 tokens de saída por tentativa. Valores reais vêm da resposta do provedor; chamadas sem uso conhecido mantêm a reserva. Preço de entrada sem desconto de cache torna a estimativa conservadora. Estimativa não é fatura ou garantia de um teto de cobrança no Azure; um limite do recurso deve complementar o controle quando disponível.

Um ledger em `.runtime/llm-budgets/`, identificado pelo hash de `approval_id`, persiste a reserva **antes** de enviar a chamada. Cópias do arquivo de autorização compartilham ledger/lock; mudar preço ou limite sem uma nova autorização é recusado. Reinício não devolve chamadas/tokens reservados. Uso medido acima da reserva interrompe a rodada, inclusive após reinício. Tokens parciais ou inconsistentes mantêm custo identificado como parcial, nunca zero conhecido. Cada etapa pode ser tentada uma vez por autorização; falha exige decisão explícita sobre outra rodada, preservando resultados. Lock que sobreviver a uma interrupção exige conferir que o processo terminou antes de removê-lo.

## Comandos preparados

Na raiz do projeto, com a imagem backend já construída e Docker disponível:

```powershell
# Sem provedor e sem tocar a base de demonstração:
docker compose --profile evaluation run --rm evaluator python -m evals.live_runner --mode offline --stage development

# Após o revisor preparar o holdout, congela código/casos sem abri-los:
docker compose --profile evaluation run --rm evaluator python -m evals.live_runner --freeze

# SOMENTE depois de configurar acesso e autorizar o gasto delimitado:
docker compose --profile evaluation run --rm evaluator python -m evals.live_runner --mode live --stage smoke --authorization /app/.runtime/live-authorization.json
docker compose --profile evaluation run --rm evaluator python -m evals.live_runner --mode live --stage development --authorization /app/.runtime/live-authorization.json
docker compose --profile evaluation run --rm evaluator python -m evals.live_runner --mode live --stage final --authorization /app/.runtime/live-authorization.json

# Encerra só o banco de testes, preservando o volume demo:
docker compose --profile evaluation stop test-db
```

O comando `--freeze` recusa sobrescrever um freeze anterior. Se desenvolvimento exigir mudança antes da avaliação final, preserve o freeze anterior com a identificação da rodada e registre o novo contrato; não renomeie resultados para aparentar aprovação. A rodada final de 24×2 tem critério fixo; resultado reprovado continua reprovado até correção e nova avaliação autorizada.

Smoke e desenvolvimento têm estados próprios; nenhum deles emite aprovação final. `live_final_approved` exige freeze válido, 48 resultados finais completos nas seis categorias, limiares aprovados, baseline estruturada íntegra e fontes/casos sem mudanças durante a execução. Quantidades de chamadas reais e decisões das guardas locais aparecem separadamente, sem remover casos difíceis do denominador.

Relatórios únicos em `evals/reports/<UTC-id>/`: manifest com fontes/ambiente, `cases.jsonl` com esperado/observado, `summary.json` e resumo Markdown. Entradas são sintéticas, saídas são planos e dados autorizados. Metadata do provedor é uma lista explícita de campos: IDs, modelo, hashes, status, duração, tentativas e uso. Nenhum header, chave, cookie, connection string ou raciocínio privado é coletado. Falhas anteriores não são sobrescritas.

## Referências conferidas em 21/09/2026

- [Azure — endpoints](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/endpoints): rota de inferência v1 e nome de deployment.
- [Azure — saída estruturada](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/structured-outputs): suporte deve ser conferido no modelo real.
- [OpenAI — contrato estruturado](https://developers.openai.com/api/docs/guides/structured-outputs): parsing e recusas; conformidade de schema não prova compreensão.
