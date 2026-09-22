# Robustez do proxy e limites da revisão

## Prazo de leitura e resposta

A inspeção do proxy mostrou que `readRequestBody(request)` era aguardado antes
da criação de `AbortSignal.timeout(45_000)` no fetch. Portanto, aquele timeout
não abrangia a leitura inicial do corpo. O limite de 16 KiB já existia, mas a
função podia continuar esperando por um próximo chunk. A hipótese não foi
transformada em prova com conexão lenta real; a correção foi validada com streams
locais controlados e deadlines curtos.

Agora o proxy inicia um prazo total de **45 segundos antes da leitura**. Esse
mesmo prazo acompanha fetch e corpo da resposta, sem reiniciar quando um chunk
chega. Uma expiração durante a leitura gera **408**; excesso de **16 KiB** continua
gerando **413**. Os dois erros mantêm request_id, no-store e nosniff. Falha do
upstream antes da resposta mantém 503.

A desconexão do cliente propaga aborto; cancelar o consumidor da resposta
interrompe o fetch. Sucesso, falha e cancelamento liberam reader, timer e listeners.
O cancelamento da origem é solicitado sem esperar indefinidamente seu hook.

O corpo da resposta segue em chunks com backpressure. Se o prazo acaba após os
cabeçalhos terem sido enviados, o stream termina com erro: não é possível
substituir aquele status por 503. O cliente não converte falha ao decodificar JSON
em null bem-sucedido; apresenta “Resposta incompleta do serviço. Tente novamente.”
O destino fixo do backend e a seleção de cabeçalhos/cookies permanecem iguais.

## Validação de 22/09/2026 UTC

- Build Docker do frontend em Next.js 16.3.5 / Node 24.19.0 aprovado, incluindo
  compilação e TypeScript de produção.
- ESLint, TypeScript e Prettier aprovados; as duas últimas mudanças também
  tiveram lint/formato direcionados e entraram no build.
- **63 casos Playwright passaram**, sem skip/retry: 28 jornadas existentes pelo
  navegador/HTTP e 35 testes puros. Os 16 testes novos em
  `frontend/e2e/proxy-streams.spec.ts` não abrem conexões lentas nem fazem carga.
- Stack `fix-loja-20260922` isolada, com PostgreSQL em tmpfs, migrações/seed,
  frontend recém-construído e backend de publicação sem alterações de código.
  `LLM_ENABLED=false` e chave vazia: nenhuma chamada ao provedor.
- Evidências históricas conferidas antes/depois pelo `verify_evidence.py`.
- Gitleaks 8.30.1 passou no histórico Git e no conteúdo preparado para o commit,
  sem achados e sem adicionar exceções à configuração existente.

Os novos casos cobrem ausência de primeiro chunk, prazo total com chunks
intermediários, aborto anterior/durante a leitura, Content-Length e bytes reais,
hooks de cancelamento pendentes, ausência de listener após encerramento, remoção
do timer, EOF, resposta sem corpo, erro upstream, prazo sem consumo downstream,
408/413 da rota, preservação dos cabeçalhos e erro explícito para JSON interrompido.
Não se somam as reexecuções locais desses mesmos casos ao total acima.

[Manifesto e hashes](evidence/proxy-deadline-20260922/manifest.json) ·
[resultado Playwright](evidence/proxy-deadline-20260922/results.json) ·
[saída da suíte](evidence/proxy-deadline-20260922/playwright.log).

Para repetir apenas os casos puros, após `npm ci` em `frontend`:

```sh
npx playwright test e2e/domain.spec.ts e2e/proxy-streams.spec.ts
```

Para a suíte completa com navegador e banco novos, use `dev.ps1 e2e`, conforme
[instalação local](local-setup.md). O CI executa a suíte completa.

## O que esta rodada não comprova

O incremento posterior de [orçamento persistente](provider-budget.md) controla admissão de chamadas no caminho LLM da aplicação. Reserva e despacho ficam em transações próprias; resultado incerto não é liberado por rollback, reinício ou prazo do proxy. Esse controle tem verificação separada e não completa a auditoria adversarial anterior de autenticação/RBAC, nem impõe limite de cobrança a outros clientes da mesma credencial.

Trata-se de revisão de robustez do transporte e regressão funcional. Não é
pentest completo, nova revisão adversarial de autenticação/RBAC, teste de carga
ou validação de implantação pública. Um timeout por requisição não limita o
número de conexões e não garante que o backend interrompa processamento já
iniciado quando o fetch é abortado. O prazo é aplicado pelo event loop; não mede
nem evita bloqueio desse event loop ou saturação do host.

Os resultados anteriores de dependências, imagens, backend e avaliação Azure
têm seus próprios artefatos e escopos em [verificação](verification.md) e
[publicação](publication-check.md); não foram convertidos em novas medições desta
rodada. Identidade de produção, política de requisições, papel SQL, backup/restore
e custo global de uso do modelo continuam requisitos a definir antes de ampliar
a demonstração local.

## Código e evidências relacionados

[limite de corpo](../frontend/src/lib/server/request-body.ts) · [prazo do proxy](../frontend/src/lib/server/proxy-lifetime.ts) · [jornadas](../frontend/e2e/proxy-streams.spec.ts).
