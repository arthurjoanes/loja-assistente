# O que o modo demo entende

Modo **Demo sem IA**: parser de padrões.

Versão `demo-patterns-v4`. Termos e números desconhecidos pedem reformulação antes da consulta. Paráfrases fora do vocabulário também são recusadas. “Quanto eu vendi ontem?”, “Me mostra o faturamento de ontem” e “Só queria saber a receita de ontem” agora preservam o plano. Saudações isoladas recebem ajuda sem consulta. Prefixos de cortesia só são removidos no início: “Só queria saber a receita somente em dinheiro” continua recusada. Isso corrige casos conhecidos; compreensão aberta depende do modelo e da avaliação separada.

| Capacidade | Exemplos e variações |
|---|---|
| Receita | Quanto vendi ontem?; Qual o faturamento?; Quanto entrou ontem? |
| Pedidos | Quantos pedidos concluídos ontem?; Quantas vendas nos últimos 7 dias? |
| Ticket | Qual o ticket médio ontem? |
| Unidades | Quantas unidades vendi ontem? |
| Ranking | Ranking de produtos por receita ontem; Quais os 5 produtos com maior receita nos últimos 7 dias?; Top 3 produtos por quantidade ontem |
| Evolução | Evolução diária da receita nos últimos 7 dias; Pedidos por dia de 2026-08-10 a 2026-08-16 |
| Comparação | Compare a receita dos últimos 7 dias com o período anterior; Compare o faturamento de ontem com anteontem |
| Continuação | E nos sete dias anteriores?; E no período anterior? |

Datas reconhecidas: ontem, anteontem, hoje, últimos N dias (1–90, completos), semana passada (segunda a domingo), este mês (até a véspera da referência), ISO `2026-08-16` e `16/08/2026`. Em intervalos humanos `de X a Y`, Y é incluído; a API transforma para fim exclusivo Y+1. Hoje pode estar fora da cobertura, o que é informado.

Texto com período explícito prevalece sobre filtro visual. Sem período no texto, usa o filtro visual; sem ambos pede esclarecimento. Referências explícitas de loja prevalecem sobre o filtro e sempre passam pela autorização. O backend aceita IDs permitidos ou nomes da lista permitida. Datas inválidas, indicador ambíguo e comparações fora dos padrões pedem reformulação. Consultas canceladas/brutas ou agrupamentos não implementados não são convertidos silenciosamente em outra métrica.

Para lojas, os padrões explícitos incluem `loja Centro`, `loja a001`, `lojas Centro e Jardins`, `lojas Centro, Jardins` e `loja Centro e da loja Jardins`. Nomes compostos são preservados como uma referência, por exemplo `loja Vila Nova`; esse exemplo só seria autorizado se existisse entre as lojas permitidas. O parser separa os nomes pelo conector `e` ou por vírgulas e encerra a lista quando encontra o período reconhecido ou pontuação. Não procura compreender listas arbitrárias em português. Nomes contendo esses separadores podem ser informados pelo ID estável.

Menções repetidas não multiplicam o escopo. Um nome composto conhecido tem prioridade sobre outro nome que seja seu prefixo. Referências desconhecidas continuam no plano mesmo ao lado de referências válidas: `Receita da loja Centro e da loja Fantasma ontem` resulta em recusa integral HTTP 403, antes de consultar vendas. A referência válida não serve como autorização para descartar a desconhecida e responder a uma pergunta diferente.

Continuação é resolvida pelo último plano validado da mesma conversa, conservando indicador e lojas e deslocando a janela. Não utiliza conversas alheias nem texto do histórico como instrução. Nenhum padrão deste arquivo concede permissão de loja.

## Filtros e ambiguidades recusados

Pagamento (`dinheiro`, `Pix`, cartão), categoria, vendedor, canal, produto individual, horário, exclusões (`exceto`, `sem`, `apenas`, `somente`) e condições de valor não fazem parte do contrato. A guarda explícita também roda antes do adaptador LLM. Exemplos: “Quanto vendi ontem somente em dinheiro?”, “Receita de canecas ontem”, “Receita por vendedor ontem”, “Receita das 10 às 14 ontem”. Resposta de esclarecimento: `plan=null`, `result=null`, sem SQL de vendas. O produto pode aparecer em ranking; isso não implementa filtro de produto.

“Receita ontem ou hoje”, dois indicadores ou ranking junto com evolução diária exigem reformulação. A política é uma métrica principal por consulta: “ticket e quantidade de pedidos” pede escolha, sem consultar SQL. Os totais auxiliares de uma consulta válida não significam que múltiplas solicitações foram compreendidas. Todas as seis combinações de pares de métricas são exercitadas com conectores “e” e “por”. Um ranking “mais vendidos **por receita**” usa receita; sem métrica monetária explícita, “mais vendidos” usa unidades. Números são aceitos somente nos formatos implementados de datas, períodos, IDs e limite de ranking. Os testes também incluem termos de negócio desconhecidos e comprovam ausência de SQL analítico, não apenas o texto da mensagem.

A ordem está explícita em `demo.interpret`: guardas de capacidade → continuação estrita → vocabulário/números → todas as métricas candidatas → período/comparação → lojas → plano validado. `demo_language.py` reúne vocabulário e capacidade; `demo_periods.py` cuida das janelas e precedências; `store_mentions.py` resolve menções. Espaços internos/quebras e acentos são normalizados, mas palavras desconhecidas continuam recusadas. A seleção do provedor está em `assistant/interpretation.py` e não conhece o banco.

Novos padrões precisam de testes com perguntas válidas e ambíguas, conferindo o plano inteiro.
