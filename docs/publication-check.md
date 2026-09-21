# Verificação para publicação

Revalidação de 21/09/2026 em uma cópia formada somente pelos arquivos públicos do Git, com configuração gerada, imagens Linux e bancos exclusivos. Não houve chamada a modelo nesta rodada. Os registros da avaliação Azure anterior foram preservados e conferidos por hash.

| Verificação | Resultado |
|---|---|
| Instalação | Build da API e frontend, migrações 0001/0002, seed e saúde dos serviços passaram em ambiente novo. |
| Backend | 313 testes passaram; Ruff, formato e mypy passaram. As 57 avaliações estão incluídas nesses testes e também passaram no runner separado. |
| Frontend | Build de produção, ESLint, TypeScript e Prettier passaram. |
| Navegador | 47 casos Playwright passaram em 37,1 s, sem falha, skip ou retry. Desktop e celular foram inspecionados nas capturas reais. |
| Roteiro HTTP | Receita, cálculo, ranking, comparação, continuação, capacidade ausente, ausência de dados, logout e isolamento entre contas passaram pelo proxy Next.js e PostgreSQL. |
| Evidências históricas | `verify_evidence.py` passou antes e depois da suíte: 65 artefatos, 62 fontes congeladas, duas bases de casos e os resultados reais 47/48 preservados. |
| Segredos | Gitleaks 8.30.1 sem credenciais detectadas no histórico após triagem de hashes de arquivo e um ID de correlação. Exceções são limitadas a caminhos e valores exatos em `.gitleaks.toml`. |

## Correções desta rodada

As imagens da aplicação passaram a usar Python 3.12.14 e Node 24.19.0 sobre Alpine 3.24, com digests fixados. A instalação Python usa o mesmo `uv.lock` e aceita apenas wheels; `uv` e `pip` não ficam no runtime. O frontend usa OpenSSL 3.5.8 e não leva npm, Yarn ou Corepack para a imagem final. Os serviços continuam executando sem usuário root.

Os atalhos de teste e avaliação agora gravam seus resultados em `evals/reports/local/`, ignorado pelo Git. Antes, sobrescreviam os relatórios históricos `latest.*`, fazendo a conferência de evidências falhar depois de uma execução normal. O runner original permanece congelado para reproduzir a avaliação; os comandos documentados passam o diretório de saída explicitamente.

O verificador do roteiro HTTP foi atualizado para converter os centavos recebidos como strings JSON em inteiros antes de somá-los. A aplicação já mantinha esse contrato para evitar perda de precisão no navegador; o script de demonstração ainda esperava números JSON.

O CI verifica o histórico com Gitleaks, bloqueia vulnerabilidades HIGH/CRITICAL nas imagens da aplicação, executa a instalação e o roteiro HTTP, e confirma que os testes não alteraram as evidências publicadas. O workflow passou no Actionlint 1.7.12; a execução remota deve ser consultada na aba Actions do repositório.

## Escopo

O scan local Trivy 0.74.0 examinou pacotes do sistema e das aplicações sem ignorar vulnerabilidades sem correção: zero achados nas duas imagens finais. A API contém 38 pacotes de sistema e 46 distribuições Python; o frontend, 18 pacotes de sistema e 20 pacotes Node. A base de vulnerabilidades e as identidades das imagens estão no [registro técnico](publication-check.json).

Esse resultado vale para os pacotes reconhecidos e para a base consultada nessa data. O scanner emitiu aviso de que Alpine 3.24 ainda não constava em sua tabela de fim de suporte; isso não impediu a análise dos pacotes. A imagem PostgreSQL e a imagem de ferramentas Playwright não fazem parte desse scan da aplicação. Ele não substitui testes de invasão nem demonstra segurança absoluta.

A entrega é uma demonstração local funcional nas capacidades documentadas. O parser tem vocabulário limitado e o modelo teve uma falha nas 48 tentativas medidas. A aplicação não foi validada como serviço de produção, para perguntas arbitrárias ou com usuários reais. [Instalação](local-setup.md), [arquitetura](architecture.md) e [método da avaliação](azure-live-results.md).
