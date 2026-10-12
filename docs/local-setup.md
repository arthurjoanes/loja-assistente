# Executar localmente

Requisitos: Docker com containers Linux e Compose v2. No Windows, use PowerShell 7; no Linux, Python 3.11 ou posterior para criar a configuração. As portas 3102 e 8102 precisam estar livres. A aplicação e os dados de demonstração são locais; nenhum recurso de nuvem é criado.

## Windows

Na raiz do clone:

```powershell
.\scripts\dev.ps1 setup
.\scripts\dev.ps1 start
```

## Linux

Na raiz do clone:

```sh
python3 scripts/setup_env.py
docker compose build backend
docker compose build frontend
docker compose up -d --wait db
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python -m loja_assistente.seed
docker compose up -d --wait
```

O gerador cria senhas aleatórias para banco e sessões no `.env` ignorado, sem sobrescrever uma configuração existente. No Linux, também usa o UID/GID atual para os arquivos gerados. O seed contém apenas organizações, contas e vendas fictícias.

Abra [a interface](http://localhost:3102), entre com `gerente.a@demo.local` e senha `LojaDemo!2026`. A pergunta **Quanto vendi ontem?** usa 16/08/2026, pois a referência analítica é fixa. O modo Demo interpreta as perguntas suportadas sem provedor externo. O [roteiro](demo.md) cobre ranking, comparação, cobertura e isolamento entre organizações.

## Verificar e encerrar

```sh
docker compose --profile test run --rm test
docker compose --profile test build frontend-check
docker compose --profile test run --rm frontend-check
docker compose -f compose.e2e.yaml build backend
docker compose -f compose.e2e.yaml build frontend
docker compose -f compose.e2e.yaml build e2e
docker compose -f compose.e2e.yaml up --abort-on-container-exit --exit-code-from e2e
docker compose -f compose.e2e.yaml down
```

Os testes usam bancos exclusivos, separados da demonstração; o banco E2E fica em memória. No Windows, os atalhos são `dev.ps1 test`, `dev.ps1 check-frontend` e `dev.ps1 e2e`.

Para parar a demonstração e manter seus dados: `docker compose --profile test down`, ou `dev.ps1 stop` no Windows. Para iniciá-la novamente: `docker compose up -d --wait`. O volume `postgres_data` conserva o histórico entre reinícios.

Este ambiente publica portas somente em `127.0.0.1`. Disponibilizar a aplicação na internet exige configuração própria de HTTPS, cookies seguros, identidade e proteção operacional. O Compose entregue executa a demonstração local.

## Verificação isolada da evolução

Pare agentes e editores que possam alterar as fontes antes da prova. Na raiz, com Python 3.11+ e Docker/Compose saudável:

```powershell
python scripts/verify_evidence.py
python scripts/prove_evolution.py --output C:/Temp/la-evo
python scripts/verify_evidence.py
```

O executor copia as fontes para uma pasta privada, confere hashes durante e após a execução e constrói imagens próprias. Registra HEAD, branch e diff, incluindo hashes dos arquivos novos que HEAD não identifica. Cada rodada usa `pf-loja-assistente-evolucao-20261012-RUN`, tags exclusivas, arquivo público de teste novo, `LLM_ENABLED=false` e chave vazia. Inventaria engine, projetos, containers, redes e rotas sem imprimir Env; escolhe subnet livre entre as redes inspecionadas. O Compose é chamado com `-p`, `--env-file` e `-f` explícitos.

A stack não publica portas. PostgreSQL de integração fica em `test-db`, exclusivo da rodada com nome `evolution_test`; o PostgreSQL da demonstração E2E fica em `db`. Testes de migração criam outro banco exclusivo terminado em `_test`. Capturas, relatórios e logs privados ficam sob a saída dessa rodada, sem usar binds históricos. O executor roda backend completo, avaliação offline, frontend-checks, demo HTTP pelo proxy, Playwright e scans de imagem; `--skip-image-scans` serve apenas ao desenvolvimento e fica registrado como omissão.

A limpeza confere projeto e label da rodada antes de remover seus containers e rede. As imagens com tags próprias ficam disponíveis para inspeção; remover essas tags após revisar o recibo é opcional. Nenhum recurso da demo ou de outra QA é encerrado. O atalho `dev.ps1 e2e` pertence ao projeto padrão e não é usado para esta rodada isolada. Se Docker não iniciar, preserve a falha no recibo e recupere a engine sem resetar banco/WSL ou mudar o daemon.

## Código e evidências relacionados

[Compose](../compose.yaml) · [gerador de configuração](../scripts/setup_env.py) · [PowerShell](../scripts/dev.ps1) · [Compose E2E](../compose.e2e.yaml).
