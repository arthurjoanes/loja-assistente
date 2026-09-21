# Evidências do Loja Assistente

Este índice liga as conclusões aos registros que as sustentam. Tudo nesta pasta pode ser lido sem conta Azure ou execução da aplicação. Dados comerciais, identidades e pedidos são fictícios; as chamadas à Azure foram realizadas em 21/09/2026.

## Comece pela avaliação real

1. Leia o [problema, resultado e limites](../azure-live-results.md).
2. Compare as [48 execuções por pergunta](azure-live/cases.md), incluindo a falha preservada.
3. Confira as [55 chamadas de modelo](azure-live/calls.md), com identificadores, tokens e origem de cada registro.
4. Consulte o [mapa de logs Azure](azure-live/README.md) para comandos, saída completa, testes e fontes congeladas.

| Evidência | Resultado observado | Origem |
|---|---|---|
| IA versus parser | 47/48 versus 24/48; 24 perguntas × 2 | [Final Azure](../../evals/reports/20260921T121255Z-a9c11d1f/summary.md) |
| Filtros estruturados | 30/30 casos aplicáveis | [Resumo estruturado](../../evals/reports/20260921T121255Z-a9c11d1f/summary.json) |
| Consumo das três etapas | 55 chamadas; 48.788 tokens; estimativa US$ 0,01550395 | [Registro de chamadas](azure-live/calls.md) |
| Backend após integração Azure | 313 testes, Ruff, formato e mypy passaram | [Log completo](azure-live/backend-checks.log) |
| Interface, revisão anterior | 47 casos Playwright; frontend não mudou na integração Azure | [Provas da revisão da interface](problem-review/README.md) |
| Aplicação local após integração | API e UI disponíveis; fonte da imagem conferida; dados preservados | [Verificação de runtime](azure-live/runtime-verification.json) |

Os 57 casos de regressão financeira/segurança já estão incluídos nos 313 testes backend. Não devem ser somados novamente. Os resultados anteriores continuam preservados como histórico; os arquivos `latest.*` são regressões offline, não a avaliação paga de IA.

## Verificar o material publicado

Na raiz do clone, com Python 3.11 ou posterior:

```sh
python scripts/verify_evidence.py
```

O comando confere os SHA-256 do [manifesto de artefatos](publication-manifest.json), os 62 arquivos de fonte e os casos congelados da avaliação, contagens por modo, chamadas, tokens, custo estimado e tabelas geradas. Usa somente os arquivos locais e a biblioteca padrão. Não roda SQL nem repete a classificação semântica: a correção financeira pode ser examinada na [fixture manual](../manual-fixture.md) e reexecutada pelos [testes do projeto](../verification.md).

O manifesto detecta alterações em relação a esta cópia. Ele não é assinatura de um terceiro nem atestado emitido pela Azure. IDs de requisição permitem correlação pelo titular do recurso; não dão acesso público ao serviço. A avaliação ocorreu antes do primeiro commit, por isso os registros originais identificam a fonte por hashes e mantêm `git_revision: null`.

As tabelas em Markdown são derivadas dos JSONL originais. Para regenerá-las: `python scripts/render_evidence.py --write`. O verificador falha quando uma tabela diverge da sua origem. Os registros originais da rodada não são reescritos por esses comandos.

## Escopo da conclusão

A amostra sustenta integração real, aplicação dos limites de consulta e correção técnica nos casos medidos. Não demonstra ganho comercial, uso com clientes, SLA de produção ou ausência universal de vulnerabilidades. A única falha do caminho com IA foi um esclarecimento desnecessário; os detalhes permanecem visíveis. O teto de US$ 15 controlou esta avaliação, sem criar limite global para consultas futuras pela interface.
