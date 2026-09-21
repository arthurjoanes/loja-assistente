# Métricas

Intervalos comerciais: America/Sao_Paulo, início incluído e fim excluído; convertidos para UTC antes do filtro. Referência analítica padrão 2026-08-17; ontem é [2026-08-16,2026-08-17). Autenticação e logs usam horário real.

- Receita líquida: soma(quantity * unit_price_cents - discount_cents) de itens de pedidos completed. Desconto é total do item, não por unidade. Cancelamento completo exclui todos os itens.
- Pedidos: COUNT DISTINCT do identificador composto tenant/pedido, após filtros.
- Ticket: receita/pedidos com Decimal, string Decimal em centavos sem arredondamento intermediário; apresentação em reais arredondada HALF_UP para duas casas; sem pedidos, null (indisponível).
- Unidades: soma quantity dos mesmos itens elegíveis.
- Ranking: por receita ou unidades decrescente, desempate product_id crescente. Limite entre 1 e 20. Nome do produto é dado não confiável, sempre escapado.
- Evolução diária: mesma receita/pedidos/ticket/unidades por data local; dias cobertos sem vendas aparecem como zero, dias ausentes não viram zero.
- Comparação: janela anterior contígua com o mesmo número de dias, mesmas lojas. Variação percentual (atual-anterior)/anterior*100, Decimal com duas casas HALF_UP. Base zero retorna null e explicação. Comparação só ocorre com cobertura completa nas duas janelas.

Períodos de 1–90 dias, em BRL. Cobertura conta pares loja/data. Ausência retorna números indisponíveis; cobertura parcial calcula os dias carregados e bloqueia comparação.

Receita é acumulada exatamente: a expressão SQL converte a quantidade para NUMERIC antes da multiplicação por preço BIGINT. O CHECK de desconto usa a mesma promoção, inclusive quando o produto supera BIGINT. Python soma inteiros; JSON serializa `revenue_cents` como string. A precisão Decimal para razão/apresentação/comparação aumenta com a magnitude, mantendo HALF_UP apenas na apresentação monetária. Testes cobrem preço acima de 2^53 e preço/quantidade nos limites BIGINT/INTEGER do banco. Valores desse tamanho são fronteiras de contrato, não dados realistas do varejo de demonstração.
