# Executar localmente

> Comandos e portas da composição local. Fontes: [Compose](../compose.yaml), [gerador de configuração](../scripts/setup_env.py), [PowerShell](../scripts/dev.ps1) e [Compose E2E](../compose.e2e.yaml). Conferência documental: **22/09/2026**.

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

Os testes usam bancos exclusivos; o banco E2E fica em memória. Não alteram o banco da demonstração. No Windows, os atalhos são `dev.ps1 test`, `dev.ps1 check-frontend` e `dev.ps1 e2e`.

Para parar a demonstração e manter seus dados: `docker compose --profile test down`, ou `dev.ps1 stop` no Windows. Para iniciá-la novamente: `docker compose up -d --wait`. O volume `postgres_data` conserva o histórico entre reinícios.

Este ambiente publica portas somente em `127.0.0.1`. Disponibilizar a aplicação na internet exige configuração própria de HTTPS, cookies seguros, identidade e proteção operacional; o Compose entregue é a demonstração local.
