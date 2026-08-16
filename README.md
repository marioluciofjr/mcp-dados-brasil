# mcp-dados-brasil

[![Made with Python](https://img.shields.io/badge/Python->=3.12-blue?logo=python&logoColor=white)](https://python.org "Ir para a página do Python")
![license - MIT](https://img.shields.io/badge/license-MIT-green)
![site - prazocerto.me](https://img.shields.io/badge/site-prazocerto.me-230023)
![linkedin - @marioluciofjr](https://img.shields.io/badge/linkedin-marioluciofjr-blue)

## Índice

* [Introdução](#introdução)
* [Sobre o mcp-dados-brasil](#sobre-o-mcp-dados-brasil)
* [Estrutura do projeto](#estrutura-do-projeto)
* [Tecnologias utilizadas](#tecnologias-utilizadas)
* [Requisitos](#requisitos)
* [Como instalar no Gemini Spark](#como-instalar-no-gemini-spark)
* [Como instalar no Claude Web](#como-instalar-no-claude-web)
* [Como instalar no ChatGPT](#como-instalar-no-chatgpt)
* [Exemplos de uso](#exemplos-de-uso)
* [Links úteis](#links-úteis)
* [Contribuições](#contribuições)
* [Licença](#licença)
* [Contato](#contato)

## Introdução

O **mcp-dados-brasil** é um servidor remoto que implementa o Model Context Protocol (MCP). Ele junta 6 fontes de dados abertas do governo brasileiro atrás de 11 tools: Pix (Banco Central), IBGE, Câmara dos Deputados, Senado Federal, Diário Oficial da União e Agência Brasil. Qualquer cliente MCP compatível chama essas tools em tempo real, pelo URL público do servidor.

Este MCP existe para um caso de uso específico: dar a uma IA generativa acesso direto a dado público brasileiro, sem instalação local e sem chave de API. Cada tool consulta a fonte oficial ao vivo e devolve o dado real — a IA nunca precisa adivinhar um número ou citar uma fonte duvidosa.

O público-alvo são equipes de checagem de fatos e a comunidade OSINT (inteligência de fontes abertas, na sigla em inglês). Por isso, o recorte de fontes prioriza transparência legislativa, diário oficial e notícias. O Pix entra como diferencial exclusivo: nenhum outro MCP brasileiro expõe hoje as estatísticas de transações do Banco Central.

O servidor usa o transporte Streamable HTTP e roda na nuvem, na Vercel, no URL `https://mcp-dados-brasil.vercel.app/mcp`. Não há login nem cadastro em nenhuma etapa, nem para conectar o MCP nem para nenhuma das 6 fontes de dados que ele consulta.

> [!IMPORTANT]
> Esse URL só aceita pedidos `POST` e `DELETE`, no formato do protocolo MCP. Se você colar o URL no navegador, ele faz um pedido `GET` e mostra a mensagem "Method Not Allowed". Isso é esperado, não é um erro. Confirma só que o servidor está no ar. Use o URL dentro de um cliente MCP, não direto no navegador.

> [!IMPORTANT]
> Este projeto é inspirado no [mcp-brasil](https://github.com/Mcp-Brasil/mcp-brasil), servidor MCP com 70 fontes de dados públicas brasileiras. O mcp-dados-brasil é um projeto **independente**, não um fork — não reaproveita código do mcp-brasil. Os créditos completos estão na seção [Sobre o mcp-dados-brasil](#sobre-o-mcp-dados-brasil).

> [!IMPORTANT]
> Cada cliente MCP decide, por conta própria, quando chamar as tools deste servidor — essa decisão não é controlada por este projeto. Em teste real, alguns clientes (ex.: Gemini Spark e ChatGPT) só chamam uma tool se você citar o nome do app no prompt, mesmo com o MCP já conectado; o Claude Web, no mesmo teste, chamou a tool sem precisar disso. Se a IA não usar o MCP sozinha, cite o nome que **você** deu ao app no passo 4 da instalação (não é fixo — cada pessoa escolhe o próprio nome ao conectar). Exemplo, supondo que você chamou o app de "DadosBrasil": `@DadosBrasil quero saber como está o Pix em Salvador e onde fica a cidade.`

> [!NOTE]
> Toda tool deste servidor é só leitura. Nenhuma tool grava, altera ou apaga dado em nenhum sistema externo. Quando uma fonte não devolve resultado, a tool diz isso — nunca inventa um dado para preencher a resposta.

## Sobre o mcp-dados-brasil

Este projeto nasceu de duas observações sobre o [mcp-brasil](https://github.com/Mcp-Brasil/mcp-brasil): (1) a documentação dele só ensina instalação local (`http://localhost:8000/mcp`), que não funciona em clientes remotos como Gemini Spark, Claude Web e ChatGPT; (2) ele não expõe as estatísticas de transações Pix do Banco Central — só cita Pix de forma indireta, via emendas parlamentares do TransfereGov. O mcp-dados-brasil resolve os dois pontos: é remoto por padrão, hospedado na Vercel, e traz o Pix como diferencial exclusivo.

O crédito ao mcp-brasil (licença MIT) é de propósito, não de código: mostrar que dado público brasileiro pode virar tool de IA sem exigir cadastro nem chave de API de quem consome.

Nem toda fonte cogitada entrou nesta primeira versão. Portal da Transparência e dados.gov.br exigem cadastro de chave — fora do escopo deste projeto. TransfereGov não expôs um endpoint de dados navegável na API pública. Consulta de candidatos do TSE exige compor um id de eleição por UF/ano sem uma busca direta disponível. Nenhuma das três entrou para não arriscar uma tool instável.

## Estrutura do projeto

É um MCP-Server em Python, com [FastMCP](https://gofastmcp.com) e transporte Streamable HTTP, seguindo Programação Orientada a Objetos: cada fonte de dados vira uma classe (`ClientePix`, `ClienteIBGE`, `ClienteCamara`, `ClienteSenado`, `ClienteDOU`, `ClienteNoticias`), com alta coesão (a classe guarda URL base, cache e métodos daquela fonte) e baixo acoplamento (nenhum módulo de `tools/` importa outro — o que é compartilhado mora em `core.py`). As funções marcadas com `@mcp.tool` são só a porta de entrada: validam a chamada do modelo e delegam para o método da classe.

### Pix — `ClientePix` (3 tools)

| Tool | O que faz |
|---|---|
| `pix_transacoes_por_municipio` | Transações Pix por município, estado e região: valores e quantidades pagas e recebidas, por pessoa física (PF) e jurídica (PJ). Parâmetros opcionais: `municipio`, `estado`, `ano_mes`, `top` (máximo 100). |
| `pix_estatisticas_nacionais` | Visão agregada nacional do Pix: perfil de pagador/recebedor, faixa etária, região, forma de iniciação e finalidade. Parâmetros opcionais: `ano_mes`, `pagador`, `recebedor`, `top` (máximo 100). |
| `pix_fraudes_contestacoes` | Contestações e fraudes por mês: Pix contestados, devoluções via MED, valor residual não devolvido. Parâmetros opcionais: `ano_mes`, `top` (máximo 60). |

### IBGE — `ClienteIBGE` (1 tool)

| Tool | O que faz |
|---|---|
| `ibge_localidades` | Código IBGE, UF e região de um município ou estado. Parâmetros opcionais: `municipio`, `estado`, `top` (máximo 50). Lista de municípios fica em cache de 24h na instância da classe. |

### Câmara dos Deputados — `ClienteCamara` (3 tools)

| Tool | O que faz |
|---|---|
| `camara_buscar_deputados` | Busca deputados por nome, estado ou partido. Parâmetro opcional `top` (máximo 50). |
| `camara_votacoes` | Votações de uma proposição (`sigla_tipo` + `numero` + `ano`), ou votos individuais de uma votação específica (`id_votacao`) quando há chamada nominal — avisa quando não há registro nominal, em vez de inventar um resultado. |
| `camara_despesas_deputado` | Despesas da CEAP de um deputado (`id_deputado` ou `nome`, `ano`, `mes` opcionais, `top` máximo 100). |

### Senado Federal — `ClienteSenado` (2 tools)

| Tool | O que faz |
|---|---|
| `senado_buscar_senadores` | Busca senadores em exercício por nome, estado ou partido (`top` máximo 81). |
| `senado_materias` | Matérias legislativas de autoria de um senador (`codigo_senador` ou `nome`, `top` máximo 50). |

### Diário Oficial da União — `ClienteDOU` (1 tool)

| Tool | O que faz |
|---|---|
| `dou_buscar_termo` | Busca um termo nas edições do DOU, por seção (`1`, `2`, `3` ou `edital`) e período (`dia`, `semana`, `mes` ou `ano`). Cache de 10 minutos por busca. `top` máximo 30. |

### Notícias — `ClienteNoticias` (1 tool)

| Tool | O que faz |
|---|---|
| `noticias_agencia_brasil` | Últimas notícias por editoria (política, economia, justiça, saúde e outras 5). `top` máximo 20 — limite fixo do próprio feed da Agência Brasil. |

## Tecnologias utilizadas

![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white)
![FastMCP](https://img.shields.io/badge/FastMCP-servidor%20MCP-000000)
![Starlette](https://img.shields.io/badge/Starlette-ASGI-052F5F)
![Uvicorn](https://img.shields.io/badge/Uvicorn-servidor%20ASGI-2A6DB2)
![httpx](https://img.shields.io/badge/httpx-cliente%20HTTP%20ass%C3%ADncrono-0B6E4F)
![Vercel](https://img.shields.io/badge/Vercel-deploy-black?logo=vercel&logoColor=white)

* **Python** — linguagem do servidor.
* **FastMCP** — framework que implementa o protocolo MCP e expõe as 11 tools via Streamable HTTP.
* **Starlette** — aplicação ASGI por baixo do FastMCP; aqui, acrescenta o CORS aberto para clientes remotos.
* **Uvicorn** — servidor ASGI usado para rodar o projeto localmente.
* **httpx** — busca cada uma das 6 fontes de dados, em tempo real, a cada chamada de tool.
* **Vercel** — hospeda o servidor remoto e disponibiliza o URL público.

## Requisitos

Para **usar** o servidor a partir de um cliente MCP (Gemini Spark, Claude Web ou ChatGPT), você não precisa instalar nada. Basta um cliente que aceite um servidor MCP remoto via Streamable HTTP, e o URL público deste servidor.

Para **rodar o projeto localmente** (desenvolvimento ou testes), instale antes:

* [Python 3.12](https://www.python.org/downloads/) ou superior.
* As dependências do projeto: `pip install -r requirements.txt`.

## Como instalar no Gemini Spark

O Gemini Spark é o modo agêntico do Gemini App.

1. Acesse a barra lateral do Gemini Web e clique em "Spark".
2. Clique na aba "Apps Conectados".
3. Desça a barra de rolagem e clique no botão "Adicionar app personalizado".
4. Cole o link do MCP (`https://mcp-dados-brasil.vercel.app/mcp`) no espaço "Adicione um link de app personalizado".
5. Clique no botão "Avançar".
6. Desça a barra de rolagem da nova tela e marque a caixa de seleção que tem a mensagem "Entendo e aceito os riscos de segurança e privacidade ao conectar este app personalizado".
7. Clique no botão "Conectar" e aguarde a próxima tela.
8. Aparecerá uma tela chamada "Salvar app personalizado". Você pode editar o nome do app.
9. Depois de conferir se está tudo certo e a tool estar listada, clique no botão "Conectar".

> Você saberá que está tudo certo se o MCP aparecer como um novo app em "Apps personalizados para o Spark".

## Como instalar no Claude Web

1. Na barra lateral do Claude Web, clique em "Personalizar".
2. Escolha a aba "Conectores".
3. Clique no botão "Adicionar" e escolha a opção "Adicionar conector personalizado".
4. Dê um nome para o conector.
5. Cole o link do MCP (`https://mcp-dados-brasil.vercel.app/mcp`) no espaço abaixo do nome que escolheu na etapa 4.
6. Clique no botão "Adicionar".
7. Clique no botão "Vincular".
8. Clique no botão "Requer aprovação" e mude para "Sempre permitir".

## Como instalar no ChatGPT

1. Na barra lateral, clique em "Plugins".
2. Clique no botão "+", que fica do lado de "Pesquisar plugins".
3. Na tela "Novo plugin", dê um nome no espaço "Nome".
4. Em "Conexão", cole o link do MCP (`https://mcp-dados-brasil.vercel.app/mcp`) e deixe a opção "URL do Servidor" habilitada.
5. Em "Autenticação", escolha a opção "Sem autenticação" (este servidor não usa OAuth).
6. Clique na caixa de seleção "Entendi e quero continuar".
7. Clique no botão "Criar".
8. Na nova tela, clique no botão "Conectar".

## Exemplos de uso

Conectou o MCP e não sabe o que perguntar? Veja **[exemplos-de-uso.md](exemplos-de-uso.md)** — um guia com 50 perguntas em linguagem natural, prontas para usar, cobrindo as 11 tools. Cada uma foi testada de verdade contra os dados reais das 6 fontes, incluindo 20 perguntas que cruzam 2 ou 3 tools ao mesmo tempo (ex.: "onde fica Cuiabá, como está o Pix por lá, e o que saiu no Diário Oficial mencionando a cidade?"). É o ponto de partida recomendado para quem quer ter ideia rápida das possibilidades antes de explorar por conta própria.

## Links úteis

* [Documentação oficial do Model Context Protocol](https://modelcontextprotocol.io/introduction) - Todos os detalhes desse protocolo da Anthropic.
* [Documentação oficial do FastMCP](https://gofastmcp.com) - Framework usado para construir o servidor MCP deste projeto.
* [Documentação da Vercel para Python](https://vercel.com/docs/functions/runtimes/python) - Como a Vercel executa uma aplicação Python/ASGI.
* [mcp-brasil](https://github.com/Mcp-Brasil/mcp-brasil) - O projeto que inspirou este MCP (ver seção Sobre).
* [API de Dados Abertos do Pix](https://olinda.bcb.gov.br/olinda/servico/Pix_DadosAbertos/versao/v1/documentacao) - Fonte oficial das 3 tools de Pix, mantida pelo Banco Central.
* [API de Localidades do IBGE](https://servicodados.ibge.gov.br/api/docs/localidades) - Fonte oficial da tool `ibge_localidades`.
* [API de Dados Abertos da Câmara dos Deputados](https://dadosabertos.camara.leg.br/swagger/api.html) - Fonte oficial das 3 tools da Câmara.
* [API de Dados Abertos do Senado Federal](https://legis.senado.leg.br/dadosabertos) - Fonte oficial das 2 tools do Senado.
* [Portal de busca do Diário Oficial da União](https://www.in.gov.br/consulta) - Fonte oficial da tool `dou_buscar_termo`, mantida pela Imprensa Nacional.
* [Agência Brasil](https://agenciabrasil.ebc.com.br/) - Fonte oficial da tool `noticias_agencia_brasil`, agência pública de notícias da EBC.

## Contribuições

Contribuições são bem-vindas! Se você tiver ideias para melhorar este projeto, sinta-se à vontade para abrir um fork do repositório.

## Licença

Este projeto está licenciado sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## Contato

Mário Lúcio - Prazo Certo®
<div>
  <a href="https://www.linkedin.com/in/marioluciofjr" target="_blank"><img src="https://img.shields.io/badge/-LinkedIn-%230077B5?style=for-the-badge&logo=linkedin&logoColor=white"></a>
  <a href = "mailto:marioluciofjr@gmail.com" target="_blank"><img src="https://img.shields.io/badge/-Gmail-%23333?style=for-the-badge&logo=gmail&logoColor=white"></a>
  <a href="https://prazocerto.me/contato" target="_blank"><img src="https://img.shields.io/badge/prazocerto.me/contato-230023?style=for-the-badge&logo=wordpress&logoColor=white"></a>
</div>
