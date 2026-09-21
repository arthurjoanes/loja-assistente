# Interface e organização

Resultado, filtros e pergunta ficam na área principal. Dados, limites e detalhes dos atendimentos ficam em painéis recolhíveis.

O resultado destaca a métrica solicitada e mantém os outros totais como contexto. Receita, ticket, pedidos e unidades têm definições próprias. O modo demo exige uma métrica principal por pergunta; não transforma “ticket e pedidos” em escolha silenciosa. Ranking explica que o total cobre todas as vendas do período/escopo, não apenas produtos exibidos. Evidência é agregada por dia, com fórmula, cobertura, lojas, datas e request_id.

Seis atalhos de consulta. Texto e controles de 14–16 px, metadados a partir de 12 px. O select usa rótulos curtos; o campo de pergunta mostra o modo escolhido.

| Estado | Comportamento |
|---|---|
| Pergunta sem conteúdo ou período inválido | Envio desabilitado; datas conservam edição e apontam para erro associado ao par. |
| Enviando | Escopo e pergunta bloqueados; proteção síncrona contra duplicação. |
| Falha de rede/conflito | Rascunho e resposta anterior preservados; usuário pode reenviar. |
| Evidência indisponível | Erro local e repetição, sem descartar resultado. Resposta de tela antiga é ignorada após troca de identidade. |
| Atendimentos sem atualização | Última amostra permanece explicitamente marcada como antiga; detalhes técnicos recolhidos por linha. |
| Nova análise | Resultado e filtros de conversa reiniciados; foco retorna à pergunta. |
| Menu móvel | Contém foco quando aberto, Escape fecha e devolve foco; fechado não recebe Tab. |

O código foi dividido por responsabilidade. `workspace.tsx` compõe UI e foco; `use-workspace.ts` coordena HTTP/sessão; `conversation-state.ts` reúne transições de estado e `period-selection.ts` trata calendário. Resultado, visualização e leitura de evidência estão em módulos separados. Não há cálculo financeiro no JSX nem framework novo.

As capturas [notebook](screenshots/welcome-1280x720.png), [celular](screenshots/welcome-390x844.png) e [consulta com evidência](screenshots/consulta-com-evidencia.png) vieram da aplicação real em ambiente E2E novo. A principal começa com uma conversa; testes de campos rodam depois. [viewport-checks.json](screenshots/viewport-checks.json) verifica seis geometrias, acesso ao fim da evidência, campo focado, alvos e ausência de overflow global; tabelas têm rolagem própria. 320×256 CSS px reproduz a geometria equivalente a 400%, sem medir zoom nativo.

CSS global exige revisão visual ao alterar seletores compartilhados. [Revisão técnica](review-round-2.md) e [testes](verification.md).
