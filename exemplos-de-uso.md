# Exemplos de uso do mcp-dados-brasil

Este guia mostra 50 perguntas em linguagem natural que você pode fazer ao conectar o mcp-dados-brasil no Gemini Spark, no Claude Web ou no ChatGPT. Cada exemplo mostra a tool (ou as tools) que o modelo chama por trás, e um trecho real da resposta — todos os 50 foram testados de verdade contra as 6 fontes de dados, em 16 de agosto de 2026, não são respostas inventadas.

Você não precisa saber o nome de nenhuma tool para usar o MCP: basta perguntar em português normal, como nos exemplos abaixo. Os nomes das tools aparecem aqui só para você entender o que está acontecendo por trás.

> [!NOTE]
> Os números (valores em R$, quantidades, datas de notícia) mudam a cada nova consulta, porque as fontes são atualizadas o tempo todo. O trecho de resposta aqui é uma fotografia do dia do teste — o formato e o tipo de informação que você recebe são o que importa reproduzir.

## Índice

* [Pix](#pix) — 7 exemplos
* [IBGE](#ibge) — 3 exemplos
* [Câmara dos Deputados](#câmara-dos-deputados) — 6 exemplos
* [Senado Federal](#senado-federal) — 4 exemplos
* [Diário Oficial da União](#diário-oficial-da-união) — 5 exemplos
* [Notícias](#notícias) — 5 exemplos
* [Perguntas que cruzam 2 ou mais tools](#perguntas-que-cruzam-2-ou-mais-tools) — 20 exemplos

## Pix

### 1. "Quanto foi movimentado em Pix por pessoa física em Belo Horizonte no último mês disponível?"
- Tool: `pix_transacoes_por_municipio(municipio="Belo Horizonte", top=1)`
- Resposta real: Belo Horizonte/MG, 202608 — pago por PF: R$ 10.368.457.472,27 em 39.779.916 transações.

### 2. "Qual o volume de Pix em Manaus?"
- Tool: `pix_transacoes_por_municipio(municipio="Manaus", top=1)`
- Resposta real: Manaus/AM, 202608 — pago por PF: R$ 7.383.299.723,34 em 60.801.159 transações.

### 3. "Como está o Pix em Curitiba?"
- Tool: `pix_transacoes_por_municipio(municipio="Curitiba", top=1)`
- Resposta real: Curitiba/PR, 202608 — pago por PF: R$ 7.493.400.602,84 em 26.923.2xx transações.

### 4. "Como está o Pix em Fortaleza, no Ceará?"
- Tool: `pix_transacoes_por_municipio(municipio="Fortaleza", estado="Ceará", top=1)`
- Resposta real: Fortaleza/CE, 202608 — pago por PF: R$ 9.223.707.250,41 em 55.552.637 transações; pago por PJ: R$ 12.051.794.075,74.
- Dica: sem o `estado`, "Fortaleza" pode trazer primeiro Fortaleza dos Nogueiras/MA — nome de cidade se repete pelo Brasil, então informe o estado quando puder.

### 5. "Qual o perfil nacional de quem paga e recebe Pix no Brasil?"
- Tool: `pix_estatisticas_nacionais(top=3)`
- Resposta real: 202607 — PF pagando PF, pagador na região Norte (faixa mais de 60 anos)... 3 registros com perfis diferentes de pagador/recebedor.

### 6. "Quanto pessoa física paga para pessoa jurídica via Pix no Brasil?"
- Tool: `pix_estatisticas_nacionais(pagador="PF", recebedor="PJ", top=2)`
- Resposta real: 202607 — PF pagando PJ, pagador sem região informada (faixa mais de 60 anos), recebedor na região Nordeste.

### 7. "Quantos Pix foram contestados por fraude e quanto foi devolvido aos usuários?"
- Tool: `pix_fraudes_contestacoes(top=3)`
- Resposta real: 202604 — 2.960.295 Pix contestados, 283.048 contestações aceitas, 2.677.247 rejeitadas.

## IBGE

### 8. "Existem municípios chamados Divinópolis no Brasil? Em quais estados?"
- Tool: `ibge_localidades(municipio="Divinópolis")`
- Resposta real: 3 resultados — Divinópolis do Tocantins/TO, Divinópolis/MG, Divinópolis de Goiás/GO.

### 9. "Quantos municípios existem chamados 'Bom Jesus' no Brasil?"
- Tool: `ibge_localidades(municipio="Bom Jesus", top=10)`
- Resposta real: 10 resultados (limite do `top`) espalhados por PA, TO, MA, PI, RN, PB, BA (2x) e MG — Bom Jesus é um dos nomes de município mais repetidos do país.

### 10. "Existe algum município chamado Santa Rita na Paraíba?"
- Tool: `ibge_localidades(municipio="Santa Rita", estado="PB", top=5)`
- Resposta real: Santa Rita/PB (Nordeste) — código IBGE 2513703.

## Câmara dos Deputados

### 11. "O que aconteceu com a votação do PL 1800/2023 na Câmara?"
- Tool: `camara_votacoes(sigla_tipo="PL", numero=1800, ano=2023, top=3)`
- Resposta real: 2 votações registradas em 2026-08-13 (órgão CCP), ambas sobre encaminhar a proposta a outras comissões — aprovadas.

### 12. "A votação do PL 1800/2023 teve registro do voto individual de cada deputado?"
- Tool: `camara_votacoes(id_votacao="2355754-35")`
- Resposta real: "não tem votos individuais registrados (provavelmente foi uma votação simbólica, sem chamada nominal)" — a tool avisa isso em vez de inventar um placar.

### 13. "Quanto o deputado Domingos Sávio (PL) gastou da cota parlamentar em julho de 2026?"
- Tool: `camara_despesas_deputado(nome="Domingos Sávio", ano=2026, mes=7, top=5)`
- Resposta real: 53 registros em julho/2026, total R$ 15.037,75 — hospedagem, combustível e corrida de Uber entre os itens mais recentes.

### 14. "Qual o total de despesas do deputado Afonso Florence (PT) em 2026?"
- Tool: `camara_despesas_deputado(id_deputado=160508, ano=2026, top=3)`
- Resposta real: 180 registros no ano, total R$ 150.176,49.

### 15. "Quais deputados do PT existem hoje na Câmara?"
- Tool: `camara_buscar_deputados(partido="PT", top=5)`
- Resposta real: 5 deputados encontrados.

### 16. "Quais deputados do PL representam Minas Gerais?"
- Tool: `camara_buscar_deputados(estado="MG", partido="PL", top=5)`
- Resposta real: 5 deputados encontrados, incluindo Domingos Sávio.

## Senado Federal

### 17. "Quais matérias o senador Camilo Santana (PT) apresentou no Senado?"
- Tool: `senado_materias(nome="Camilo Santana", top=3)`
- Resposta real: RQS 538/2026 — requerimento pela liderança do PT de destaque para votação em separado de uma emenda ao PLP 18/2021, e mais 2 matérias.

### 18. "O que o senador Alan Rick (REPUBLICANOS) propôs no Senado?"
- Tool: `senado_materias(nome="Alan Rick", top=3)`
- Resposta real: RQS 202/2023 — sessão especial pelos 75 anos do Estado de Israel, e mais 2 requerimentos.

### 19. "Quais senadores são do PT?"
- Tool: `senado_buscar_senadores(partido="PT", top=5)`
- Resposta real: 5 senadores encontrados.

### 20. "Quem são os senadores do Acre?"
- Tool: `senado_buscar_senadores(estado="AC")`
- Resposta real: 3 senadores encontrados, entre eles Alan Rick.

## Diário Oficial da União

### 21. "Saiu alguma portaria sobre concurso público no Diário Oficial este mês?"
- Tool: `dou_buscar_termo(termo="concurso público", periodo="mes", top=3)`
- Resposta real: PORTARIA MF Nº 2.433, de 14 de agosto de 2026, entre 3 resultados encontrados.

### 22. "Teve alguma nomeação de pessoal publicada recentemente no Diário Oficial?"
- Tool: `dou_buscar_termo(termo="nomeação", secao="2", periodo="mes", top=3)`
- Resposta real: PORTARIA DE PESSOAL SE/MAPA Nº 1.032, de 13 de agosto de 2026, na seção 2 (atos de pessoal).

### 23. "Saiu alguma portaria de saúde no Diário Oficial esta semana?"
- Tool: `dou_buscar_termo(termo="saúde", secao="1", periodo="semana", top=2)`
- Resposta real: PORTARIA SAES/MS Nº 4.288, sobre cuidados paliativos, entre 2 resultados.

### 24. "Existe alguma publicação sobre Pix no Diário Oficial da União este mês?"
- Tool: `dou_buscar_termo(termo="Pix", periodo="mes", top=2)`
- Resposta real: EDITAL Nº 720/2026-TCU/SEPROC, de 13 de agosto de 2026, sobre cobrança de débito.

### 25. "Saiu alguma publicação sobre meio ambiente no Diário Oficial este mês?"
- Tool: `dou_buscar_termo(termo="meio ambiente", periodo="mes", top=2)`
- Resposta real: EDITAL Nº 7/2026, ligado à Secretaria de meio ambiente, entre 2 resultados.

## Notícias

### 26. "Quais as últimas notícias de economia no Brasil?"
- Tool: `noticias_agencia_brasil(editoria="economia", top=2)`
- Resposta real: "Projeto mapeia caminhos para economia verde no Nordeste" (16/08/2026) entre as 2 mais recentes.

### 27. "O que saiu de notícia política recentemente?"
- Tool: `noticias_agencia_brasil(editoria="politica", top=2)`
- Resposta real: "TSE determina remoção de vídeo que associa Lula ao PCC e ao CV" (16/08/2026).

### 28. "Quais as últimas notícias sobre saúde?"
- Tool: `noticias_agencia_brasil(editoria="saude", top=2)`
- Resposta real: "Com 25 anos, grupo musical de pacientes psiquiátricos lança novo álbum" (15/08/2026).

### 29. "O que aconteceu recentemente na Justiça brasileira?"
- Tool: `noticias_agencia_brasil(editoria="justica", top=2)`
- Resposta real: "Bolsonaro pede ao STF para se consultar com a nora, que é dentista" (14/08/2026).

### 30. "Quais as últimas notícias internacionais?"
- Tool: `noticias_agencia_brasil(editoria="internacional", top=2)`
- Resposta real: "Terremoto na Indonésia deixa pelo menos 47 mortos" (15/08/2026).

## Perguntas que cruzam 2 ou mais tools

Estes exemplos mostram o valor de ter várias fontes no mesmo MCP: uma pergunta só, respondida com 2 ou 3 tools diferentes, sem você precisar abrir vários apps separados. O IBGE se destaca aqui — sozinho ele só devolve código e localização, mas cruzado com Pix ou com o Diário Oficial, vira o ponto de partida de uma pesquisa completa sobre um lugar.

### 31. "Onde fica Rio Branco, no Acre, e saiu alguma publicação mencionando a cidade no Diário Oficial este ano?"
- Tools: `ibge_localidades(municipio="Rio Branco")` + `dou_buscar_termo(termo="Rio Branco", periodo="ano", top=2)`
- Resposta real: Rio Branco/AC, código IBGE 1200401, região Norte — e a Pauta da 11ª Sessão Ordinária do Senado, publicada no DOU, cita a cidade.

### 32. "Onde fica Florianópolis, e o que saiu no Diário Oficial sobre a cidade este ano?"
- Tools: `ibge_localidades(municipio="Florianópolis")` + `dou_buscar_termo(termo="Florianópolis", periodo="ano", top=2)`
- Resposta real: Florianópolis/SC, código IBGE 4205407, região Sul — e a Portaria nº 19.780, de 11 de agosto de 2026, menciona a cidade.

### 33. "Onde fica Palmas, no Tocantins, e saiu algo no Diário Oficial mencionando a cidade?"
- Tools: `ibge_localidades(municipio="Palmas", estado="TO")` + `dou_buscar_termo(termo="Palmas", periodo="ano", top=2)`
- Resposta real: Palmas/TO, código IBGE 1721000, região Norte — e a Portaria GM/MS nº 10.345 cita a cidade.

### 34. "Onde fica Salvador, na Bahia, e como está o Pix por lá?"
- Tools: `ibge_localidades(municipio="Salvador", estado="BA")` + `pix_transacoes_por_municipio(municipio="Salvador", estado="Bahia", top=1)`
- Resposta real: Salvador/BA, código IBGE 2927408 — e R$ 9,45 bilhões pagos por PF via Pix em 202608, em 59.812.652 transações.

### 35. "Onde fica Porto Alegre, no Rio Grande do Sul, e como está o Pix por lá?"
- Tools: `ibge_localidades(municipio="Porto Alegre", estado="RS")` + `pix_transacoes_por_municipio(municipio="Porto Alegre", estado="Rio Grande do Sul", top=1)`
- Resposta real: Porto Alegre/RS, código IBGE 4314902 — e R$ 5,20 bilhões pagos por PF via Pix em 202608.
- Dica: sem o `estado`, "Porto Alegre" pode trazer primeiro Porto Alegre do Norte/MT — outro caso de nome de cidade repetido.

### 36. "Onde fica Recife, e como está o Pix por lá?"
- Tools: `ibge_localidades(municipio="Recife")` + `pix_transacoes_por_municipio(municipio="Recife", top=1)`
- Resposta real: Recife/PE, código IBGE 2611606 — e R$ 5,75 bilhões pagos por PF via Pix em 202608.

### 37. "Onde fica Boa Vista, a capital mais ao norte do Brasil, e quais as últimas notícias de direitos humanos no país?"
- Tools: `ibge_localidades(municipio="Boa Vista", estado="RR")` + `noticias_agencia_brasil(editoria="direitos-humanos", top=2)`
- Resposta real: Boa Vista/RR, código IBGE 1400100, região Norte — e a notícia "Publicação lembra 50 anos do atentado à sede da ABI na ditadura" (15/08/2026).

### 38. "Teve fraude de Pix recentemente? Saiu alguma publicação sobre Pix no Diário Oficial?"
- Tools: `pix_fraudes_contestacoes(top=1)` + `dou_buscar_termo(termo="Pix", periodo="mes", top=2)`
- Resposta real: 2.960.295 Pix contestados em abril/2026 — e um edital do TCU sobre cobrança de débito de Pix, publicado em agosto/2026.

### 39. "Saiu alguma portaria de saúde no Diário Oficial, e quais as últimas notícias de saúde?"
- Tools: `dou_buscar_termo(termo="saúde", secao="1", periodo="mes", top=2)` + `noticias_agencia_brasil(editoria="saude", top=2)`
- Resposta real: portaria sobre cuidados paliativos no DOU — e notícia sobre um grupo musical de pacientes psiquiátricos na Agência Brasil.

### 40. "Quais as últimas notícias de justiça, e o que saiu no Diário Oficial sobre nomeações de pessoal?"
- Tools: `noticias_agencia_brasil(editoria="justica", top=2)` + `dou_buscar_termo(termo="nomeação", secao="2", periodo="mes", top=2)`
- Resposta real: notícia sobre Bolsonaro e o STF — e a Portaria de Pessoal SE/MAPA Nº 1.032, publicada na seção 2 do DOU.

### 41. "Localize o deputado Afonso Florence (PT), e me mostre quanto ele gastou da cota parlamentar em 2026"
- Tools: `camara_buscar_deputados(nome="Afonso Florence")` + `camara_despesas_deputado(id_deputado=160508, ano=2026, top=3)`
- Resposta real: id 160508 localizado (PT/BA) — e 180 despesas em 2026, total R$ 150.176,49.

### 42. "Quais deputados do PL são de Minas Gerais, e quanto o Domingos Sávio gastou da cota em julho de 2026?"
- Tools: `camara_buscar_deputados(estado="MG", partido="PL", top=5)` + `camara_despesas_deputado(nome="Domingos Sávio", ano=2026, mes=7, top=3)`
- Resposta real: 5 deputados do PL em MG encontrados — e Domingos Sávio gastou R$ 15.037,75 em julho/2026, em 53 registros.

### 43. "O que o senador Camilo Santana (PT) propôs, e quem mais é do PT no Senado?"
- Tools: `senado_materias(nome="Camilo Santana", top=2)` + `senado_buscar_senadores(partido="PT", top=5)`
- Resposta real: 2 matérias de autoria de Camilo Santana — e 5 senadores do PT encontrados.

### 44. "Quantos deputados e quantos senadores o PT tem hoje?"
- Tools: `camara_buscar_deputados(partido="PT", top=5)` + `senado_buscar_senadores(partido="PT", top=5)`
- Resposta real: 5 deputados e 5 senadores do PT encontrados (o `top` limita a lista, não o total real do partido).

### 45. "A proposição PL 1800/2023 foi votada na Câmara? Ela propõe criar uma universidade federal — saiu algo relacionado no Diário Oficial este ano?"
- Tools: `camara_votacoes(sigla_tipo="PL", numero=1800, ano=2023, top=2)` + `dou_buscar_termo(termo="universidade federal", periodo="ano", top=2)`
- Resposta real: 2 votações de encaminhamento aprovadas em agosto/2026 — e uma portaria do Ministério da Fazenda mencionando execução orçamentária de universidade federal.

### 46. "O senador Alan Rick (REPUBLICANOS) propôs alguma matéria recentemente, e quem mais é senador pelo Acre?"
- Tools: `senado_materias(nome="Alan Rick", top=2)` + `senado_buscar_senadores(estado="AC")`
- Resposta real: 2 requerimentos de autoria de Alan Rick — e 3 senadores encontrados representando o Acre.

### 47. "Compare o volume de Pix entre Salvador e Recife"
- Tools: `pix_transacoes_por_municipio(municipio="Salvador", estado="Bahia", top=1)` + `pix_transacoes_por_municipio(municipio="Recife", top=1)`
- Resposta real: Salvador, R$ 9,45 bilhões pagos por PF; Recife, R$ 5,75 bilhões — ambos em 202608.

### 48. "Onde fica Cuiabá, e o que saiu recentemente no Diário Oficial mencionando a cidade?"
- Tools: `ibge_localidades(municipio="Cuiabá")` + `dou_buscar_termo(termo="Cuiabá", periodo="ano", top=2)`
- Resposta real: Cuiabá/MT, código IBGE 5103403, região Centro-Oeste — e a Decisão SUROD nº 1.010, de 7 de agosto de 2026, cita a cidade.

### 49. "Dê um raio-x de Cuiabá: onde fica, como está o Pix por lá, e saiu alguma publicação recente no Diário Oficial mencionando a cidade"
- Tools: `ibge_localidades(municipio="Cuiabá")` + `pix_transacoes_por_municipio(municipio="Cuiabá", top=1)` + `dou_buscar_termo(termo="Cuiabá", periodo="ano", top=2)`
- Resposta real: código IBGE 5103403, região Centro-Oeste; dado de Pix do mês mais recente; e a Decisão SUROD nº 1.010 no Diário Oficial — as 3 fontes numa pergunta só.

### 50. "Dê um raio-x de Belo Horizonte: onde fica, como está o Pix por lá, e quais deputados do PL representam Minas Gerais?"
- Tools: `ibge_localidades(municipio="Belo Horizonte")` + `pix_transacoes_por_municipio(municipio="Belo Horizonte", top=1)` + `camara_buscar_deputados(estado="MG", partido="PL", top=3)`
- Resposta real: código IBGE 3106200, região Sudeste; R$ 10,37 bilhões em Pix por PF em 202608; e 3 deputados do PL em MG encontrados.
