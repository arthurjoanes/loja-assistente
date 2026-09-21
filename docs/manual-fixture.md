# Fixture financeira manual v1

Fixture independente do gerador e das funções de cálculo. Referência: 17/08/2026, America/Sao_Paulo. Cobertura de 10/08 a 16/08 para a001, a002 e b001; de 10 a 13/08, zero vendas. A API usa fim exclusivo.

Os três usuários têm os mesmos emails/senha fictícios documentados para o demo, em um banco PostgreSQL dedicado de testes. O gerente A acessa a001, o supervisor A a001/a002, e o gerente B b001. Identificadores externos STORE-001, PROD-001 e ORDER-001 coincidem entre organizações.

| Pedido | Loja | Instante UTC | Itens, em centavos | Receita | Unidades |
|---|---|---|---|---:|---:|
| oa1 | A/Centro | 15/08 02:59:59 | Caneca 2×1000−100; Garrafa 1×600 | 2500 | 3 |
| oa2 | A/Centro | 15/08 03:00:00 | Caneca 1×1000; Ecobag 3×200 | 1600 | 4 |
| oa3 | A/Centro | 16/08 15:00 | Garrafa 2×600−200; Ecobag 5×200 | 2000 | 7 |
| oa4 | A/Centro | 16/08 16:00 | Caneca 1×1000 | 1000 | 1 |
| oa5 | A/Centro | 16/08 17:00 | Caneca 10×1000; cancelado | excluído | excluído |
| oa6 | A/Jardins | 16/08 18:00 | Caneca 1×1000; Garrafa 1×600 | 1600 | 2 |
| ob1 | B/Centro | 16/08 19:00 | Caneca 2×1700−100 | 3300 | 2 |

Há sete pedidos, onze itens e 21 linhas de cobertura. O desconto é total do item. O pedido oa1 pertence ao dia comercial 14/08 e oa2 a 15/08, apesar de ambos terem data UTC 15/08.

## Resultados calculados à mão

- Centro A, 14–16/08: receita 2500+1600+2000+1000 = **7100 centavos**; **4 pedidos distintos**; 3+4+7+1 = **15 unidades**; ticket 7100/4 = **1775 centavos**.
- Centro A, ontem: 2000+1000 = **3000 centavos**, **2 pedidos**, **8 unidades**, ticket **1500 centavos**.
- Centro A, dia anterior: **1600 centavos**, **1 pedido**, **4 unidades**, ticket **1600 centavos**.
- Receita ontem versus anterior: (3000−1600)/1600×100 = **87,50%**; ticket (1500−1600)/1600×100 = **−6,25%**.
- Supervisor A, ontem: 3000+1600 = **4600 centavos**, **3 pedidos**, **10 unidades**, ticket exato 4600/3 centavos; apresentação **R$ 15,33**.
- Gerente B, ontem: **3300 centavos**, **1 pedido**, **2 unidades**, ticket **R$ 33,00**.
- Série Centro A 14–16/08: **[2500, 1600, 3000]**.
- Ranking por receita: Caneca **3900**, Garrafa **1600**, Ecobag **1600**. Desempate por product_id crescente.
- Ranking por quantidade: Ecobag **8**, Caneca **4**, Garrafa **3**.
- Base anterior 11–13/08 = zero: percentual de comparação indisponível.
- Dia 09/08: cobertura ausente, números indisponíveis. Janela 09–14/08: cobertura parcial, apenas receita carregada identificada como tal; comparação recusada.

O JSON de avaliações mantém esses números literais. Eles não são calculados pelo gerador nem pelo código sob teste. Fixtures de teste usam transação externa e savepoints, revertidos ao final; o nome do banco precisa terminar em _test. Nenhum teste usa SQLite ou apaga dados da demonstração.
