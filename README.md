# Loja Assistente

Faça perguntas sobre vendas e confira os números em tabela ou gráfico. Cada resultado informa o período, as lojas consideradas, o cálculo e a cobertura dos dados. O histórico permite rever perguntas anteriores sem recalcular os indicadores. A demonstração usa dados fictícios.

O problema é responder à pergunta certa dentro do acesso da conta. “Quanto vendi ontem somente em dinheiro?” não pode virar o total de todas as formas de pagamento. O servidor aceita apenas capacidades representáveis, autoriza as lojas e faz a conta no PostgreSQL; a interface mantém o recorte junto dos números. [Problema, solução e critérios](docs/problem-solution.md) · [decisões e código](docs/decisoes-tecnicas.md).

![Evolução diária de vendas com lojas, período e cálculo](docs/screenshots/operational-proof-20260922/f98ee94864384422bd835bcabd8f3a11/01-calculation.png)

*Aplicação real em modo Demo, com dados sintéticos. [Consulta, recusa e nova tentativa válida](docs/operational-story.md), com versões, testes e limites da prova.*

## Conferir uma análise

1. Entre com uma conta demo e pergunte **Mostre a evolução diária da receita nos últimos 7 dias**. Confira as lojas e o período exibidos no resultado. Datas escritas na pergunta prevalecem sobre o filtro.
2. Alterne **Gráfico** e **Tabela**. Abra **Cálculo** para conferir fórmula, totais por dia e cobertura. Um dia carregado sem vendas tem zero; um dia ausente não é tratado como zero.
3. Faça outra pergunta e use **Resultados desta análise** para rever a primeira. A continuação **E nos sete dias anteriores?** usa o último plano válido da conversa, mesmo enquanto um resultado anterior está selecionado.

[Guia da interface](docs/interface.md) · [matriz de qualidade e limites](docs/frontend-quality.md) · [roteiro completo](docs/demo.md) · [três situações verificadas](docs/operational-story.md).

## Dá pra conferir sem rodar

Não precisa subir o projeto nem ter chave de IA:

```sh
python scripts/verify_evidence.py
```

O script usa só a biblioteca padrão do Python 3.11+ e recalcula as contagens a partir dos arquivos de resultado. Confere também as fontes históricas contra o freeze original e informa diferenças do código atual; não atribui a avaliação antiga às mudanças posteriores. O detalhe está em [resultado e limites](docs/azure-live-results.md), [as 48 execuções lado a lado](docs/evidence/azure-live/cases.md) e [as 55 chamadas à Azure](docs/evidence/azure-live/calls.md).

## Interpretação e cálculo separados

A IA interpreta a pergunta. O servidor valida o plano, checa a autorização e faz a conta no banco; texto, tabela e gráfico usam o mesmo resultado. Isso está em [analytics/contracts.py](backend/src/loja_assistente/analytics/contracts.py), [auth/service.py](backend/src/loja_assistente/auth/service.py) e [analytics/queries.py](backend/src/loja_assistente/analytics/queries.py). [Arquitetura](docs/architecture.md).

Na avaliação histórica com GPT-5.6 Luna no Azure Foundry, o caminho modelo + backend acertou 47/48 tentativas, contra 24/48 do parser determinístico, em 24 perguntas repetidas duas vezes. As chamadas foram reais; os dados comerciais são sintéticos e a falha está documentada. Esse recorte não mede a qualidade de toda pergunta possível nem foi repetido na revisão visual.

## Rodar

Docker Desktop com engine Linux e PowerShell 7+:

```powershell
.\scripts\dev.ps1 setup
.\scripts\dev.ps1 start
```

[App](http://localhost:3102) · [API](http://localhost:8102/docs). O setup cria `.env`, faz o build, migra e carrega o seed. Entre com `gerente.a@demo.local`, senha `LojaDemo!2026`, e pergunte **Quanto vendi ontem?**. Abra **Cálculo** para conferir o resultado. As contas de demonstração só autenticam com `DEMO_MODE=true`; o relógio analítico é 17/08/2026.

O modo Demo funciona sem chave nem chamadas pagas. Para habilitar o modelo, siga a [configuração OpenAI/Azure](docs/llm-integration.md). [Instalação no Linux e comandos de operação](docs/local-setup.md).

O modo com modelo tem cobrança do provedor. Na avaliação histórica, 55 chamadas somaram 48.788 tokens e US$ 0,01550395 estimados; isso não é uma fatura nem previsão para outro uso. O teto de US$ 15 daquele experimento não limita as chamadas da interface. [Consumo, preços registrados e limites](docs/azure-live-results.md#chamadas-e-consumo).

O caminho LLM da API exige [orçamento persistente por organização](docs/provider-budget.md): reserva antes do despacho, sem saldo automático, e uso incerto continua comprometido após falha ou reinício. Os tetos locais controlam admissão; não são uma garantia de cobrança monetária do provedor.

## Testes

`dev.ps1 test` roda os testes de backend; a rodada desta entrega aprovou 353 casos, incluindo 40 novos casos ligados ao orçamento e seu executor. A avaliação offline também passou em 57/57. `dev.ps1 e2e` roda jornadas e casos puros: a revisão final aprovou 68, sendo 38 puros e 30 de navegador/HTTP. Build, tipos, lint e formato passaram. [Resultados, tentativas e escopo de cada revisão](docs/verification.md). O refinamento posterior de alinhamento, foco e composição de texto também passou na rodada final `f98ee948`, com 68 casos e três capturas novas. Os 11 testes de integridade histórica foram executados separadamente no host. [Escopo do candidato](docs/frontend-quality.md).

O proxy limita a entrada a 16 KiB e usa um prazo total de 45 s para receber o corpo e encaminhar a resposta. Leitura expirada retorna 408; corpo excessivo retorna 413. Uma resposta interrompida é apresentada como falha, sem virar resultado vazio. [Contrato e testes de robustez](docs/security.md).

## Limites

Cada pergunta escolhe uma métrica. "Quanto vendi ontem só em dinheiro?" pede esclarecimento em vez de chutar o total. Pagamento, vendedor, categoria, produto e horário não cabem no plano atual, e comparações exigem cobertura completa. A base tem 6.316 pedidos fictícios em 90 dias, sem lucro, estoque, imposto ou reembolso parcial. Os testes de protocolo não medem compreensão de português, e não medi ganho de produtividade com usuários reais. [Parser demo](docs/demo-parser.md) · [métricas](docs/metrics.md) · [decisões técnicas](docs/decisoes-tecnicas.md).

FastAPI, PostgreSQL, SQLAlchemy/Alembic, Next.js/TypeScript. Licença MIT.
