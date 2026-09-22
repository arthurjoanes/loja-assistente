# Ler e conferir uma análise

Consulte a [jornada com três capturas atuais](operational-story.md) para acompanhar consulta, recusa e nova tentativa válida. Os [resultados de validação](verification.md) identificam as versões e as correções de contraste/foco.

Os filtros definem lojas e período para a próxima consulta. Datas escritas na pergunta têm precedência; as lojas continuam sujeitas à autorização no servidor. O resultado conserva o recorte efetivamente consultado, mesmo depois de mudar um filtro.

No desktop, **Próxima consulta** reúne controles e pergunta à esquerda; o resultado ocupa a área maior à direita. Até 1024 px, a preparação fica recolhida inicialmente e abre depois do resultado por **Editar pergunta**. A barra do produto reúne Análises, Atendimentos e Nova análise; **Histórico** abre as conversas anteriores. Dados de acesso e métricas ficam em um bloco recolhível.

**Editar pergunta**, no cabeçalho do resultado, abre a preparação quando necessário e leva o foco ao campo sem abrir outra conversa ou executar uma consulta. Ela permanece aberta enquanto você trabalha; **Recolher próxima consulta** devolve o foco ao botão de edição. Isso permite continuar a análise mesmo depois de abrir um cálculo longo no celular.

## Perguntas e resultados

A pergunta consultada é o título da resposta. Quando a conversa tem mais de uma resposta, o seletor **Resultados desta análise** permite escolher uma delas. Trocar a seleção só muda a leitura: não chama o interpretador, não executa SQL e não altera o resultado. A visualização gráfico/tabela e o cálculo já aberto permanecem naquela resposta.

Uma nova resposta passa a ser o resultado selecionado. Perguntas anteriores continuam no seletor; conversas anteriores ficam no histórico pessoal. **Nova análise** abre uma conversa vazia e leva o foco ao campo **Pergunta**.

Durante a consulta, **Consultando…** aparece antes do resultado anterior. Uma falha mostra o aviso de erro e preserva a análise já recebida; a pergunta pode ser corrigida ou enviada novamente. Não há reenvio automático.

**E nos sete dias anteriores?** continua o último plano válido da conversa. Selecionar um resultado antigo não muda essa referência. Um aviso junto da pergunta esclarece isso durante a revisão de uma resposta anterior.

## Números e cobertura

O indicador principal corresponde à métrica solicitada. Os demais indicadores descrevem o mesmo período e as mesmas lojas. No ranking, o total considera todos os produtos, não apenas os itens exibidos.

Gráfico e tabela usam as mesmas linhas recebidas do servidor. **Cálculo** busca a evidência daquela resposta e apresenta fórmula, lojas, fuso comercial, período com fim exclusivo, fonte, cobertura e totais por dia. Uma falha ao carregar o cálculo permite tentar novamente sem apagar o resultado.

A evolução diária reserva uma posição por data do período, na largura disponível, e no máximo três datas no eixo. As colunas partem de zero e usam a mesma cor; um traço indica dado ausente ou valor indisponível, diferente de zero. Datas sem linha carregada mantêm sua posição no calendário, sem inventar linhas ou vendas na tabela. A descrição acessível distingue a lacuna, e **Tabela** preserva as linhas e os valores exatos recebidos do servidor, mesmo em séries de 30 dias. O ranking usa barras horizontais e destaca a primeira posição. **Resumo em texto** conserva a descrição do backend sem repetir inicialmente os indicadores. Avisos de cobertura parcial, ausência de dados e esclarecimento permanecem visíveis.

- **Cobertura completa:** todas as combinações de loja e dia esperadas estão carregadas; um dia coberto sem vendas pode ter valor zero.
- **Cobertura parcial:** o aviso acompanha os números; abra o cálculo para identificar combinações ausentes. Os totais são parciais.
- **Sem dados carregados:** não há total numérico para esse recorte.
- **Esclarecimento ou capacidade ausente:** a resposta explica a restrição; um total geral não substitui silenciosamente a pergunta.

O bloco **Dados fictícios · acesso e métricas** informa as lojas da conta e a referência analítica. **Demo sem IA** e **Interpretação com IA** indicam o modo da resposta, independentemente do modo escolhido para a próxima pergunta.

## Consulta em telas menores

O menu lateral abre pelo botão **Abrir menu**, mantém o foco dentro da navegação e fecha com Escape. O seletor de resultados e as tabelas respondem ao teclado. A página rola normalmente; tabelas largas têm sua própria rolagem. O painel de acesso e os cálculos podem ser recolhidos para reduzir o conteúdo visível.

## Atendimentos

Mostra até 100 consultas da conta, com modo, capacidade, status e durações registradas. **Ver detalhes** apresenta o ID e a versão do interpretador. Esses tempos medem o serviço antes da gravação do log, não a latência completa percebida no navegador. Tokens e custo continuam indisponíveis nesse painel.
