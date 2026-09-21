# Registro legível das chamadas Azure

[Resultado e método](../../azure-live-results.md) · [48 execuções finais](cases.md)

**55 chamadas reais registradas**, com 45,307 tokens de entrada, 3,481 de saída e 48,788 no total. Cada chamada terminou como `completed`, com `attempts=1` e uso conhecido. Os separadores numéricos desta página seguem o formato dos logs (vírgula para milhares, ponto para decimais).

As linhas abaixo vêm dos três runs oficiais de 21/09/2026. O gerador confere chamadas, tokens e estimativa de custo contra o `summary.json` de cada run. Não soma `budget.calls_reserved`, tokens reservados ou custos reservados: esses campos são cumulativos entre etapas.

**Estimativa conservadora total: US$ 0.01550395.** Cálculo: `(45307 × 0.25 + 3481 × 1.20) / 1.000.000`. Adota US$ 0.25 por milhão para toda entrada (incluindo margem para cache write) e US$ 1.20 para saída. Os [preços salvos](azure-prices.json) foram consultados antes do experimento. **Estimativa não é fatura**; não houve conferência do faturamento Azure.

`provider_request_id` e `response_id` são identificadores de rastreabilidade retornados pelo serviço, **não credenciais**. Eles permitem correlação por alguém com acesso autorizado aos registros Azure; sua presença nestes arquivos não constitui verificação independente no provedor. O repositório preserva o registro do cliente, sem corpo bruto da API, cabeçalhos de autenticação ou conteúdo de raciocínio do modelo.

`Duração provedor` é o intervalo medido pelo adaptador local ao chamar o serviço, incluindo comunicação e SDK; não é uma métrica interna de processamento da Azure. O tempo completo da aplicação está na página de casos.

## Somas por etapa

| Etapa / fonte | Início UTC | Chamadas | Entrada | Saída | Total | Estimativa US$ |
| --- | --- | --- | --- | --- | --- | --- |
| [smoke](../../../evals/reports/20260921T121119Z-883376fa/summary.json) | `2026-09-21T12:11:19.048298+00:00` | 1 | 810 | 70 | 880 | 0.0002865 |
| [development](../../../evals/reports/20260921T121149Z-c53a402a/summary.json) | `2026-09-21T12:11:49.887215+00:00` | 12 | 9841 | 737 | 10578 | 0.00334465 |
| [final](../../../evals/reports/20260921T121255Z-a9c11d1f/summary.json) | `2026-09-21T12:12:55.108795+00:00` | 42 | 34656 | 2674 | 37330 | 0.0118728 |
| **Total** | — | **55** | **45307** | **3481** | **48788** | **0.01550395** |

O final possui 48 execuções do fluxo LLM e 42 chamadas Azure. As seis decisões de guarda local não geraram chamadas e, portanto, não aparecem nesta tabela de consumo.

## Todas as 55 chamadas

A coluna de origem abre a linha exata do JSONL que contém a pergunta, o resultado e os metadados completos permitidos.

| # | Etapa | Caso | Rep. | Modelo retornado | provider_request_id | response_id | Entrada | Saída | Duração provedor (ms) | Origem |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | smoke | dev-01 | 1 | `gpt-5.6-luna` | `e99df25a-514c-487a-ae36-72646e79786b` | `resp_0eb65bb56ec12080016ab11ee9cca88194a1a5ff487cd8297a` | 810 | 70 | 2514 | [JSONL L3](../../../evals/reports/20260921T121119Z-883376fa/cases.jsonl#L3) |
| 2 | development | dev-01 | 1 | `gpt-5.6-luna` | `6f52e846-fdc2-422c-8d4a-e821174d5424` | `resp_0472f535ee692605016ab11f0847908193a0edf93762d470ba` | 810 | 70 | 2304 | [JSONL L3](../../../evals/reports/20260921T121149Z-c53a402a/cases.jsonl#L3) |
| 3 | development | dev-02 | 1 | `gpt-5.6-luna` | `e0db70ae-8960-477d-904a-84b6d3c14ce4` | `resp_010d3aa5a6e36931016ab11f0ab08c819690155f2227af9534` | 812 | 70 | 1779 | [JSONL L6](../../../evals/reports/20260921T121149Z-c53a402a/cases.jsonl#L6) |
| 4 | development | dev-03 | 1 | `gpt-5.6-luna` | `88048b90-dd44-4997-8bc1-e1fa43b93ac0` | `resp_01d73a929187f4b7016ab11f0cd9188190968d13daed157cea` | 812 | 70 | 2164 | [JSONL L9](../../../evals/reports/20260921T121149Z-c53a402a/cases.jsonl#L9) |
| 5 | development | dev-04 | 1 | `gpt-5.6-luna` | `6e271aec-b1b9-4161-9a40-68bd95576a93` | `resp_0dda0aaba15f15b1016ab11f0f12448194944cee4587971e3d` | 806 | 33 | 1695 | [JSONL L11](../../../evals/reports/20260921T121149Z-c53a402a/cases.jsonl#L11) |
| 6 | development | dev-05 | 1 | `gpt-5.6-luna` | `7595c7ba-4bd9-4e76-bfaf-527bb2b44c2f` | `resp_01681bbd8a0cd0e2016ab11f10e1b8819794a6caf2e2e8e47d` | 813 | 31 | 1860 | [JSONL L13](../../../evals/reports/20260921T121149Z-c53a402a/cases.jsonl#L13) |
| 7 | development | dev-06 | 1 | `gpt-5.6-luna` | `2fb30c1d-ddca-4ccb-98bd-def892facf49` | `resp_01cde241ab2c78a6016ab11f12f3888197a4eb816f45ce0211` | 811 | 41 | 3436 | [JSONL L15](../../../evals/reports/20260921T121149Z-c53a402a/cases.jsonl#L15) |
| 8 | development | dev-07 | 1 | `gpt-5.6-luna` | `4af5614e-f5a9-4be4-a3f9-85f8c249afd1` | `resp_0079b9849e4d0b45016ab11f16a8b88197861a9c2d20aa3c06` | 829 | 73 | 2257 | [JSONL L18](../../../evals/reports/20260921T121149Z-c53a402a/cases.jsonl#L18) |
| 9 | development | dev-08 | 1 | `gpt-5.6-luna` | `9ab0bab5-2d10-4b68-b425-e6ded923ff50` | `resp_077b22a72723dd4e016ab11f194d448195920c2cc1ce6f119c` | 811 | 70 | 2327 | [JSONL L21](../../../evals/reports/20260921T121149Z-c53a402a/cases.jsonl#L21) |
| 10 | development | dev-09 | 1 | `gpt-5.6-luna` | `d04d1ccc-1985-4082-8dca-946f189cb294` | `resp_0bf6715a749e366a016ab11f1ba5dc8196a160a8c10e8abacf` | 811 | 70 | 1963 | [JSONL L24](../../../evals/reports/20260921T121149Z-c53a402a/cases.jsonl#L24) |
| 11 | development | dev-10 | 1 | `gpt-5.6-luna` | `e9d399e9-6633-49b8-ac3f-554cffa3fb9e` | `resp_0fb1817b5c665c80016ab11f1dee3c819799ae5abaf23992ab` | 871 | 69 | 1967 | [JSONL L27](../../../evals/reports/20260921T121149Z-c53a402a/cases.jsonl#L27) |
| 12 | development | dev-11 | 1 | `gpt-5.6-luna` | `6e2fb1c1-79bb-4d16-a578-5b587f546c68` | `resp_013db5e313e907a6016ab11f201f248190bb9440c957d58655` | 827 | 70 | 1751 | [JSONL L30](../../../evals/reports/20260921T121149Z-c53a402a/cases.jsonl#L30) |
| 13 | development | dev-12 | 1 | `gpt-5.6-luna` | `bb1da5fc-e12c-4a20-9811-e810c7dbbeb2` | `resp_0706f7e10c0c4d3f016ab11f2239a081979b0f9cf89fb98ce6` | 828 | 70 | 2167 | [JSONL L33](../../../evals/reports/20260921T121149Z-c53a402a/cases.jsonl#L33) |
| 14 | final | final-nl-01 | 1 | `gpt-5.6-luna` | `20b529fb-f0ff-4035-9114-cdda8e7408d9` | `resp_084d3ed7a5c8fd6a016ab11f49a884819581dac6b059ec360a` | 830 | 69 | 2533 | [JSONL L3](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L3) |
| 15 | final | final-nl-02 | 1 | `gpt-5.6-luna` | `b37ebbcf-8fa0-4f45-8da6-a60b39f3317b` | `resp_020b4c353d438a90016ab11f4c08288193b11fe7bd3562b60b` | 816 | 69 | 1722 | [JSONL L6](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L6) |
| 16 | final | final-nl-03 | 1 | `gpt-5.6-luna` | `0d502945-9a9d-4da5-8c99-af1743a2926b` | `resp_06210902cd4bd90d016ab11f4e11208194be98b62a604d92a0` | 826 | 70 | 3586 | [JSONL L9](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L9) |
| 17 | final | final-nl-04 | 1 | `gpt-5.6-luna` | `7100d751-61e9-420b-be71-d49ff507e411` | `resp_003e633b7461a737016ab11f51d5308195aef1862ef6ea1e10` | 825 | 70 | 1603 | [JSONL L12](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L12) |
| 18 | final | final-pc-01 | 1 | `gpt-5.6-luna` | `5de23883-7ccf-4a7a-bb49-d112514cc2c1` | `resp_0b8ee6e80d31c9de016ab11f53b6708195931f3e51429b2673` | 876 | 70 | 1874 | [JSONL L15](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L15) |
| 19 | final | final-pc-02 | 1 | `gpt-5.6-luna` | `27b484b4-280c-4ae3-b446-f63df44bedc3` | `resp_0b2410ab5eb03127016ab11f55d1e08193991e61749fefd142` | 827 | 69 | 1789 | [JSONL L18](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L18) |
| 20 | final | final-pc-03 | 1 | `gpt-5.6-luna` | `55c03f93-da32-4c70-ad0b-0a47292905e0` | `resp_051de70b937e9efe016ab11f57eaec8194a1c10bbb9fd7743f` | 819 | 71 | 2128 | [JSONL L21](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L21) |
| 21 | final | final-pc-04 | 1 | `gpt-5.6-luna` | `ff33cb65-b9b6-47d6-aa3d-1579c1a6204e` | `resp_0d058ac80c31465a016ab11f5a41cc81909ace416720e54ea5` | 832 | 70 | 1778 | [JSONL L24](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L24) |
| 22 | final | final-sc-01 | 1 | `gpt-5.6-luna` | `b3efb4eb-45c5-4907-8dd7-e5b710b2ca44` | `resp_069ce186a43138b0016ab11f5c4940819792abedbfd320f847` | 833 | 73 | 2266 | [JSONL L27](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L27) |
| 23 | final | final-sc-02 | 1 | `gpt-5.6-luna` | `606d189a-1443-4669-9c39-72b532046cf1` | `resp_02ac15860091dda9016ab11f5ec6c481938842b1e960e72926` | 819 | 69 | 1638 | [JSONL L30](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L30) |
| 24 | final | final-sc-03 | 1 | `gpt-5.6-luna` | `3fba0e45-0d3a-45d6-882c-501fe0e3ff7c` | `resp_0cb2c90c67b71df8016ab11f60a6288190b16fa43c23a3c6c0` | 830 | 69 | 1834 | [JSONL L33](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L33) |
| 25 | final | final-sc-04 | 1 | `gpt-5.6-luna` | `a28714b7-0722-495d-b420-cc613b99b206` | `resp_04bcd0953ef06185016ab11f62a42481979262f296a8202377` | 822 | 73 | 2040 | [JSONL L35](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L35) |
| 26 | final | final-uf-04 | 1 | `gpt-5.6-luna` | `5e944b15-f20e-47b6-9086-d20295c5a840` | `resp_080a54d8580156aa016ab11f65559081938534de33c820d44c` | 824 | 57 | 2055 | [JSONL L43](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L43) |
| 27 | final | final-ag-01 | 1 | `gpt-5.6-luna` | `611c5f03-a7a0-4183-a97e-01cb7272bcad` | `resp_0ba2bb7055528fa6016ab11f676da08190b1de46218663a312` | 814 | 46 | 1803 | [JSONL L45](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L45) |
| 28 | final | final-ag-02 | 1 | `gpt-5.6-luna` | `b62c3f12-dcf2-4991-84a8-74dc591070b2` | `resp_0832fbe337095c7a016ab11f6a59b48197bd0fccf3090a5afb` | 806 | 44 | 3145 | [JSONL L47](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L47) |
| 29 | final | final-ag-03 | 1 | `gpt-5.6-luna` | `e1c827de-3f60-4024-876a-9106e843cc22` | `resp_0a031e2366a12cb2016ab11f6cae888194ab672ac93455ee77` | 819 | 41 | 2093 | [JSONL L49](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L49) |
| 30 | final | final-ag-04 | 1 | `gpt-5.6-luna` | `be4154c8-8456-444d-bdd5-45b6e2bafbe5` | `resp_0520f6d8f57b103c016ab11f6ee8c88194bdcae945a520f5e3` | 818 | 36 | 1690 | [JSONL L51](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L51) |
| 31 | final | final-bf-01 | 1 | `gpt-5.6-luna` | `cd117b03-af92-4527-a0e1-036fab5df32c` | `resp_06b11de584d9b9f0016ab11f70dde08190acd7d795d54044ef` | 820 | 69 | 1877 | [JSONL L54](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L54) |
| 32 | final | final-bf-02 | 1 | `gpt-5.6-luna` | `75767a7f-cec7-47ce-aebe-4335759e02fe` | `resp_0d3c485cd020e44b016ab11f72eb50819391833b2157d46d54` | 823 | 68 | 1722 | [JSONL L57](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L57) |
| 33 | final | final-bf-03 | 1 | `gpt-5.6-luna` | `137e7814-f090-42b6-af28-078497aa0141` | `resp_021b91f9e0fd83cd016ab11f74e1888190924c0060cb6804f1` | 819 | 69 | 1882 | [JSONL L60](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L60) |
| 34 | final | final-bf-04 | 1 | `gpt-5.6-luna` | `f8aa259d-7867-4b72-9f0d-4b8dd8a320d9` | `resp_0821082ab9a869f1016ab11f770e8c8194b8026edc0b7fe6ee` | 830 | 70 | 3699 | [JSONL L63](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L63) |
| 35 | final | final-nl-01 | 2 | `gpt-5.6-luna` | `36ab563e-e899-4690-bda2-486764a8bef2` | `resp_0b25530d23c8deb6016ab11f7aea888193b0d1b25b8f908f0c` | 830 | 69 | 2080 | [JSONL L66](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L66) |
| 36 | final | final-nl-02 | 2 | `gpt-5.6-luna` | `3e5649af-445b-4bb3-998c-dcb21e3650bc` | `resp_0415fc53f5152453016ab11f7d31ac8194b91acfefad00cbb7` | 816 | 69 | 1656 | [JSONL L69](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L69) |
| 37 | final | final-nl-03 | 2 | `gpt-5.6-luna` | `b12c3778-386e-4017-9b30-ea8af9bdc658` | `resp_095b0a0939de7a37016ab11f7f1c188195af7cdeb085dd4ba1` | 826 | 70 | 3326 | [JSONL L72](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L72) |
| 38 | final | final-nl-04 | 2 | `gpt-5.6-luna` | `c18db757-6f90-47cd-ae30-16e20e9a5ba9` | `resp_06e835e1f85f7068016ab11f82b45081978bde1e3ee63d4a7d` | 825 | 70 | 1968 | [JSONL L75](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L75) |
| 39 | final | final-pc-01 | 2 | `gpt-5.6-luna` | `5adeb95c-14f6-4987-a545-2eb818b0edc2` | `resp_028ad1f9799f07fa016ab11f84efa48193befef560b9e3b4a8` | 876 | 70 | 1714 | [JSONL L78](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L78) |
| 40 | final | final-pc-02 | 2 | `gpt-5.6-luna` | `74b86427-ec81-47c0-aca3-f7d07ecef8ed` | `resp_0bc02d8c7b43cf5e016ab11f86da048190a5a7d6c352c06ddd` | 827 | 69 | 2044 | [JSONL L81](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L81) |
| 41 | final | final-pc-03 | 2 | `gpt-5.6-luna` | `23bfd16a-3647-4b4a-ae4b-419850a87135` | `resp_0cffcbaa4cb0d1b7016ab11f891a8881908efba0fa3d1c02ed` | 819 | 71 | 2021 | [JSONL L84](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L84) |
| 42 | final | final-pc-04 | 2 | `gpt-5.6-luna` | `70b5a94c-8e87-461e-94a0-73d99619d1e4` | `resp_01a684b092537905016ab11f8b6d78819485c012c3c5145d3a` | 832 | 70 | 2161 | [JSONL L87](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L87) |
| 43 | final | final-sc-01 | 2 | `gpt-5.6-luna` | `f4666553-f03e-4221-955a-d66a0d27cab5` | `resp_0e403590a3afa464016ab11f8dc84881909168049e81c74c86` | 833 | 73 | 2012 | [JSONL L90](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L90) |
| 44 | final | final-sc-02 | 2 | `gpt-5.6-luna` | `510a5e82-20c9-4c1e-b979-64f3968ab073` | `resp_0c75e64e9f5f933f016ab11f90063881948e85e2510ca5d6f5` | 819 | 69 | 1885 | [JSONL L93](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L93) |
| 45 | final | final-sc-03 | 2 | `gpt-5.6-luna` | `b0965b6d-22f9-4848-b947-561ec9a33425` | `resp_0b5fb72944d1a96e016ab11f9223c08197adf621bd80d1b801` | 830 | 69 | 2100 | [JSONL L96](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L96) |
| 46 | final | final-sc-04 | 2 | `gpt-5.6-luna` | `974488b5-5a15-4f2c-ac43-b7f85960396b` | `resp_01b3086039bc14e2016ab11f9467248194aef6324f5f54f037` | 822 | 73 | 1922 | [JSONL L98](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L98) |
| 47 | final | final-uf-04 | 2 | `gpt-5.6-luna` | `d99c54a4-6578-496b-84e9-74a1febd1b8c` | `resp_0a9847035853f585016ab11f977ebc8196846e49f8cd889cd8` | 824 | 60 | 2839 | [JSONL L106](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L106) |
| 48 | final | final-ag-01 | 2 | `gpt-5.6-luna` | `1e628456-a5e8-49ca-97f6-33f5d837b253` | `resp_0de9dcc1976c4a9f016ab11f99dc988197a672d2d955636988` | 814 | 50 | 1802 | [JSONL L108](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L108) |
| 49 | final | final-ag-02 | 2 | `gpt-5.6-luna` | `a1814bb9-8ec7-465c-be98-4b4afcc1af26` | `resp_09d76088c8b57806016ab11f9c3e708193bb6baeaee0fec67c` | 806 | 32 | 2538 | [JSONL L110](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L110) |
| 50 | final | final-ag-03 | 2 | `gpt-5.6-luna` | `125d9846-6ead-403e-a02d-8090763bf857` | `resp_07c89308f5dbed88016ab11f9e7cd48193bb8a3e49c4240c8b` | 819 | 39 | 2000 | [JSONL L112](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L112) |
| 51 | final | final-ag-04 | 2 | `gpt-5.6-luna` | `e2b655d2-5239-491e-9e49-1af2ffcbbadc` | `resp_059d126c5d086454016ab11fa0c4e08195bca6f5c954342936` | 818 | 40 | 1950 | [JSONL L114](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L114) |
| 52 | final | final-bf-01 | 2 | `gpt-5.6-luna` | `28aa8cc0-61d8-4492-9cd6-c31ebe776283` | `resp_0141198c1a0b003d016ab11fa2ccec81908533f3920494e853` | 820 | 69 | 1749 | [JSONL L117](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L117) |
| 53 | final | final-bf-02 | 2 | `gpt-5.6-luna` | `a94c2b77-0ca4-43f8-b569-60e1c98b0869` | `resp_0bb9a363cfb100ad016ab11fa4c5008193806b465ef28b5855` | 823 | 68 | 1970 | [JSONL L120](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L120) |
| 54 | final | final-bf-03 | 2 | `gpt-5.6-luna` | `860f867d-fd41-495e-9c42-542834e07fdc` | `resp_0ba237afac1a3d07016ab11fa706c48194acf7999b18436225` | 819 | 69 | 1766 | [JSONL L123](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L123) |
| 55 | final | final-bf-04 | 2 | `gpt-5.6-luna` | `917e9ca6-98d9-4083-bc46-81e869e9d045` | `resp_0764fc0b5e8e063c016ab11fa9084481908a6eb42dee1e273d` | 830 | 63 | 2278 | [JSONL L126](../../../evals/reports/20260921T121255Z-a9c11d1f/cases.jsonl#L126) |

Página derivada dos registros originais. Gerador: [render_evidence.py](../../../scripts/render_evidence.py).
Para conferir offline, na raiz do repositório: `python scripts/render_evidence.py --check`.
Para regenerar: `python scripts/render_evidence.py --write`. Requer Python 3.11+; não usa SDK, Docker, chave ou rede.
