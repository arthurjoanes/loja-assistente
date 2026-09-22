# Interface e organização

O [guia da interface](interface.md) explica pergunta, resultado selecionado, recorte aplicado, cobertura e cálculo. A [revisão de qualidade](frontend-quality.md) registra inventário de telas/estados, matriz das 11 dimensões antes/depois, decisões, referências, verificações e pendências.

A composição atual coloca o resultado à frente, com preparação da próxima consulta em área própria, histórico recolhível e cálculo sob demanda. A divisão entre coordenação de sessão/HTTP, transições da conversa, filtros, resultado, visualização e cálculo preserva a separação entre interpretação e conta feita pelo servidor.

As imagens [notebook](screenshots/welcome-1280x720.png), [celular](screenshots/welcome-390x844.png) e [consulta com cálculo](screenshots/consulta-com-evidencia.png), assim como [viewport-checks.json](screenshots/viewport-checks.json), são **evidências da interface anterior**. Não validam a reconstrução atual. A [história operacional](operational-story.md) contém capturas mais recentes e a rodada de 68 verificações das fontes que identifica. Para os incrementos posteriores desta revisão de qualidade, as 30 jornadas de navegador/HTTP e novas capturas continuam não executadas pelo bloqueio de inicialização; build e testes puros têm escopo separado em [verificação](verification.md).

## Prova posterior da candidata

A rodada `f98ee94864384422bd835bcabd8f3a11` passou em 68 casos, com build/checks e três capturas reais da candidata. [Escopo executado](verification.md#validação-final-da-candidata-de-interface) e [história com os mesmos dados](operational-story.md). Este resultado posterior não transforma os limites da revisão estática acima em uma auditoria visual completa.
