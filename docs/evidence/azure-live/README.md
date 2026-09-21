# Logs da integração Azure Foundry

Execução de 21/09/2026, GPT-5.6 Luna, versão `2026-07-09`, Azure OpenAI v1. O [relatório principal](../../azure-live-results.md) explica o problema e os critérios. Para leitura direta, abra a [comparação por pergunta](cases.md) e o [registro das chamadas](calls.md).

## Execuções preservadas

| Etapa | Resumo | Dados por caso | Saída do comando | Comando, horários e código de saída |
|---|---|---|---|---|
| Smoke, 1 chamada | [Markdown](../../../evals/reports/20260921T121119Z-883376fa/summary.md) | [JSONL](../../../evals/reports/20260921T121119Z-883376fa/cases.jsonl) | [Log](smoke-console.log) | [Recibo](smoke-command.json) |
| Desenvolvimento, 12 chamadas | [Markdown](../../../evals/reports/20260921T121149Z-c53a402a/summary.md) | [JSONL](../../../evals/reports/20260921T121149Z-c53a402a/cases.jsonl) | [Log](development-console.log) | [Recibo](development-command.json) |
| Final, 42 chamadas + 6 guardas locais | [Markdown](../../../evals/reports/20260921T121255Z-a9c11d1f/summary.md) | [JSONL](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl) | [Log](final-console.log) | [Recibo](final-command.json) |

Cada pasta de execução contém também `summary.json` com as métricas e `manifest.json` com ambiente, modelo, fonte e configuração. Os arquivos são os registros salvos na execução, incluindo resultados reprovados.

## Como ler um caso

| Campo do JSONL | Significado |
|---|---|
| `id`, `repetition`, `mode` | Pergunta, repetição e caminho: parser (`demo`), filtros (`structured`) ou modelo + backend (`llm`) |
| `expected` | Status, plano e valores esperados pela fixture manual |
| `observed` | Resposta recebida do backend, incluindo plano e cálculo quando disponíveis |
| `assessment` | Resultado das verificações; `passed` exige mais que HTTP 200 |
| `sales_queries` | Quantidade de consultas analíticas executadas; uma recusa não deve consultar o total geral |
| `provider` | Lista de chamadas ao modelo; vazia para decisões locais |
| `provider_request_id`, `response_id` | Identificadores retornados pelo provedor, preservados para correlação |
| `input_tokens`, `output_tokens`, `total_tokens` | Uso informado pelo provedor; não estimado pelo tamanho do texto |
| `duration_ms` | Na raiz, tempo do fluxo; dentro de `provider`, tempo da chamada ao modelo |

O JSONL final contém 126 linhas: 48 do parser, 30 de filtros estruturados e 48 do caminho com IA. Apenas 42 dessas últimas fizeram inferência. Uma lista `provider` vazia não indica chamada Azure. O sucesso de transporte (`provider.status = completed`) também não equivale a resposta correta: a falha `final-bf-04`, repetição 2, recebeu uma resposta completa e reprovou na avaliação.

A comparação do plano é semântica, conforme [semantic.py](../../../evals/semantic.py): a ordem das lojas é normalizada e `limit` só é relevante em ranking. Por isso um agregado pode passar com `limit` diferente do esperado; ele não limita os pedidos usados no total. Os valores financeiros esperados continuam sendo conferidos.

## Testes, configuração e integridade

| Assunto | Registro |
|---|---|
| 313 testes backend, lint, formato e tipos | [backend-checks.log](backend-checks.log) |
| Build da imagem avaliada na entrega | [backend-build.log](backend-build.log) |
| Atualização da aplicação local | [demo-refresh.log](demo-refresh.log) |
| Modelo, região e autorização sem credencial | [connection-and-authorization.json](connection-and-authorization.json) |
| Medidores e preços consultados | [azure-prices.json](azure-prices.json) |
| Fonte congelada antes da execução | [freeze-azure-luna-r1.json](freeze-azure-luna-r1.json) |
| Freeze anterior, mantido como histórico | [freeze-before-azure-configuration.json](freeze-before-azure-configuration.json) |
| Alterações anteriores ao novo freeze | [pre-live-change-review.json](pre-live-change-review.json) |
| Runtime, hashes da imagem e preservação dos dados | [runtime-verification.json](runtime-verification.json) e [estado anterior](demo-before.json) |
| Conferência final das contagens e do freeze | [final-review.json](final-review.json) |
| Integridade dos arquivos publicados | [Manifesto SHA-256](../publication-manifest.json) e [verificador offline](../../../scripts/verify_evidence.py) |

Os números de links e arquivos examinados em `final-review.json` referem-se ao momento daquela conferência, anterior à organização desta documentação.

O endpoint identifica o recurso utilizado; a chave, cabeçalhos de autorização, cookies e arquivos operacionais privados não são necessários para ler estes logs. Nenhum dos comandos de leitura/verificação executa chamadas pagas. Uma nova avaliação segue o [protocolo](../../live-evaluation.md).
