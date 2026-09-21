# Loja Assistente

Consulte vendas em português e confira a origem de cada número. O assistente transforma a pergunta em um plano limitado, autoriza o acesso às lojas e calcula no PostgreSQL. A resposta inclui período, filtros, cobertura dos dados e cálculo. A demonstração roda localmente com dados fictícios.

![Consulta de vendas](docs/screenshots/consulta-com-evidencia.png)

FastAPI, PostgreSQL, SQLAlchemy/Alembic e Next.js/TypeScript. Na avaliação com GPT-5.6 Luna no Azure Foundry, o caminho modelo + backend acertou 47/48 tentativas, contra 24/48 do parser determinístico, em 24 perguntas repetidas duas vezes. As chamadas foram reais; os dados comerciais são sintéticos e a falha está documentada.

## Dá pra conferir sem rodar

Não precisa subir o projeto nem ter chave de IA:

```sh
python scripts/verify_evidence.py
```

O script usa só a biblioteca padrão do Python 3.11+ e recalcula as contagens a partir dos arquivos de resultado. O detalhe está em [resultado e limites](docs/azure-live-results.md), [as 48 execuções lado a lado](docs/evidence/azure-live/cases.md) e [as 55 chamadas à Azure](docs/evidence/azure-live/calls.md).

## Por que a IA não inventa o total

A IA interpreta a pergunta. O servidor valida o plano, checa a autorização e faz a conta no banco; texto, tabela e gráfico usam o mesmo resultado. Isso está em [analytics/contracts.py](backend/src/loja_assistente/analytics/contracts.py), [auth/service.py](backend/src/loja_assistente/auth/service.py) e [analytics/queries.py](backend/src/loja_assistente/analytics/queries.py). [Arquitetura](docs/architecture.md).

## Rodar

Docker Desktop com engine Linux e PowerShell 7+:

```powershell
.\scripts\dev.ps1 setup
.\scripts\dev.ps1 start
```

[App](http://localhost:3102) · [API](http://localhost:8102/docs). O setup cria `.env`, faz o build, migra e carrega o seed. Entre com `gerente.a@demo.local`, senha `LojaDemo!2026`, e pergunte **Quanto vendi ontem?**. Abra **Cálculo** para conferir o resultado. As contas de demonstração só autenticam com `DEMO_MODE=true`; o relógio analítico é 17/08/2026.

O modo Demo funciona sem chave nem chamadas pagas. Para habilitar o modelo, siga a [configuração OpenAI/Azure](docs/llm-integration.md). [Instalação no Linux e comandos de operação](docs/local-setup.md).

## Testes

`dev.ps1 test` roda 313 testes de backend, incluindo 57 avaliações de regressão offline; `dev.ps1 e2e` roda 47 casos no Playwright. Comandos e resultados em [verificação](docs/verification.md).

## Limites

Cada pergunta escolhe uma métrica. "Quanto vendi ontem só em dinheiro?" pede esclarecimento em vez de chutar o total. Pagamento, vendedor, categoria, produto e horário não cabem no plano atual, e comparações exigem cobertura completa. A base tem 6.316 pedidos fictícios em 90 dias, sem lucro, estoque, imposto ou reembolso parcial. Os testes de protocolo não medem compreensão de português, e não medi ganho de produtividade com usuários reais. [Parser demo](docs/demo-parser.md) · [métricas](docs/metrics.md) · [decisões técnicas](docs/decisoes-tecnicas.md).

FastAPI, PostgreSQL, SQLAlchemy/Alembic, Next.js/TypeScript. Licença MIT.
