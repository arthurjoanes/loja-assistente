# Qualidade do frontend

Leia [docs/frontend-quality.md](docs/frontend-quality.md) antes de alterar telas: inventário, matriz das 11 dimensões, decisões e limites de validação. O [guia da interface](docs/interface.md) define seleção, continuação, recorte aplicado e cobertura.

- Preserve cálculos, autorização, contratos, modo demo e orçamento/provedor. Frontend não inventa totais nem transforma ausência em zero.
- Registre hashes do estado atual, incluindo arquivos não rastreados, antes de trabalhar sobre mudanças concorrentes. Integre apenas arquivos revisados.
- Execute lint, tipos, build e testes pertinentes. Compare capturas com os mesmos dados, perfil, pergunta, filtros e dimensões. Captura histórica e teste puro não comprovam uma jornada nova.
- Registre verificações bloqueadas. Não declare aprovação visual, acessibilidade integral ou produtividade sem executar a avaliação correspondente.
