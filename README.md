# mcp-dados-brasil

![Licença](https://img.shields.io/badge/licença-MIT-blue)
![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![FastMCP](https://img.shields.io/badge/FastMCP-3.x-informational)
![Transporte](https://img.shields.io/badge/transporte-Streamable%20HTTP-success)

Servidor MCP (Model Context Protocol) remoto com dados públicos do Brasil. Conecta direto no Gemini Spark, no Claude Web e no ChatGPT — sem instalação local, sem chave de API e sem cadastro.

> [!IMPORTANT]
> Este projeto é inspirado no [mcp-brasil](https://github.com/Mcp-Brasil/mcp-brasil), um servidor MCP com 70 fontes de dados públicas brasileiras. O mcp-dados-brasil é um projeto **independente**, não um fork. Ele nasceu de duas observações sobre o projeto original: (1) a documentação dele só ensina instalação local (`http://localhost:8000/mcp`), que não funciona em clientes remotos como Gemini Spark, Claude Web e ChatGPT; (2) ele não expõe as estatísticas de transações Pix do Banco Central. O mcp-dados-brasil resolve os dois pontos: é remoto por padrão e traz o Pix como diferencial. Os créditos ao trabalho original do mcp-brasil estão na seção [Créditos](#créditos).

> [!NOTE]
> Toda tool deste servidor é só leitura. Nenhuma tool grava, altera ou apaga dado em nenhum sistema externo.

## Índice

- [O que é](#o-que-é)
- [Fontes de dados e tools](#fontes-de-dados-e-tools)
- [Tecnologias](#tecnologias)
- [Como instalar](#como-instalar)
- [Arquitetura do código](#arquitetura-do-código)
- [Créditos](#créditos)
- [Licença](#licença)
- [Contato](#contato)

## O que é

O mcp-dados-brasil junta 6 fontes de dados abertos do governo brasileiro atrás de 11 tools de um único servidor MCP. Você pergunta em linguagem natural, no seu cliente de IA. O servidor consulta a fonte oficial e devolve a resposta.

O público-alvo é equipes de checagem de fatos e a comunidade OSINT (sigla em inglês para "inteligência de fontes abertas"). Por isso, o recorte de fontes prioriza transparência legislativa, diário oficial e notícias — além do Pix, que nenhum outro MCP brasileiro cobre hoje.

Todas as fontes são públicas e gratuitas. Nenhuma exige cadastro, chave de API ou login.

## Fontes de dados e tools

### Pix (Banco Central)

| Tool | O que faz |
|---|---|
| `pix_transacoes_por_municipio` | Estatísticas de transações Pix por município, estado e região: valores e quantidades pagas e recebidas, por pessoa física (PF) e pessoa jurídica (PJ). |
| `pix_estatisticas_nacionais` | Visão agregada nacional do Pix: perfil de pagador e recebedor, faixa etária, região, forma de iniciação (ex.: DICT, QR Code) e finalidade. |
| `pix_fraudes_contestacoes` | Contestações e fraudes do Pix por mês: quantidade de Pix contestados, valores devolvidos pelo MED (Mecanismo Especial de Devolução) e valor residual não devolvido. |

Fonte: [API de Dados Abertos do Pix](https://olinda.bcb.gov.br/olinda/servico/Pix_DadosAbertos/versao/v1/documentacao), Banco Central do Brasil.

### IBGE

| Tool | O que faz |
|---|---|
| `ibge_localidades` | Código IBGE, UF e região de um município ou estado brasileiro. |

Fonte: [API de Localidades do IBGE](https://servicodados.ibge.gov.br/api/docs/localidades).

### Câmara dos Deputados

| Tool | O que faz |
|---|---|
| `camara_buscar_deputados` | Busca deputados federais por nome, estado ou partido. |
| `camara_votacoes` | Lista as votações de uma proposição (ex.: PL 1.800/2023). Devolve também os votos individuais de uma votação específica, quando ela teve chamada nominal. |
| `camara_despesas_deputado` | Despesas da Cota para Exercício da Atividade Parlamentar (CEAP) de um deputado, por ano e mês. |

Fonte: [API de Dados Abertos da Câmara dos Deputados](https://dadosabertos.camara.leg.br/swagger/api.html).

### Senado Federal

| Tool | O que faz |
|---|---|
| `senado_buscar_senadores` | Busca senadores em exercício por nome, estado ou partido. |
| `senado_materias` | Lista as matérias legislativas (projetos de lei, requerimentos etc.) de autoria de um senador. |

Fonte: [API de Dados Abertos do Senado Federal](https://legis.senado.leg.br/dadosabertos).

### Diário Oficial da União

| Tool | O que faz |
|---|---|
| `dou_buscar_termo` | Busca um termo nas edições do Diário Oficial da União (DOU), por seção e período. |

Fonte: busca pública da Imprensa Nacional, em [in.gov.br/consulta](https://www.in.gov.br/consulta). A API oficial do DOU (WS-INCom) é restrita a órgãos de governo, e o INLABS exige cadastro — por isso esta tool usa a mesma busca pública que o site oficial oferece, sem login.

### Notícias

| Tool | O que faz |
|---|---|
| `noticias_agencia_brasil` | Últimas notícias por editoria (política, economia, justiça, saúde e outras), via RSS. |

Fonte: [Agência Brasil](https://agenciabrasil.ebc.com.br/), agência pública de notícias da EBC (Empresa Brasil de Comunicação).

## Tecnologias

| Tecnologia | Função no projeto |
|---|---|
| [Python 3.12+](https://www.python.org/) | Linguagem do servidor. |
| [FastMCP](https://gofastmcp.com/) | Framework do servidor MCP, com transporte Streamable HTTP. |
| [httpx](https://www.python-httpx.org/) | Cliente HTTP assíncrono para consultar cada fonte de dados. |
| [Starlette](https://www.starlette.io/) + [Uvicorn](https://www.uvicorn.org/) | Aplicação ASGI e servidor local. |
| [Vercel](https://vercel.com/) | Hospedagem remota do servidor. |

## Como instalar

O servidor já está no ar. Você só precisa conectar o link dele no seu cliente de IA. Troque `{{URL_MCP}}` pela URL informada depois do deploy.

Esta conexão não pede login nem senha. Ela é aberta, sem autenticação.

### Como instalar no Gemini Spark

O Gemini Spark é o modo agêntico do Gemini App.

1. Acesse a barra lateral do Gemini Web e clique em "Spark".
2. Clique na aba "Apps Conectados".
3. Desça a barra de rolagem e clique no botão "Adicionar app personalizado".
4. Cole o link do MCP (`{{URL_MCP}}`) no espaço "Adicione um link de app personalizado".
5. Clique no botão "Avançar".
6. Desça a barra de rolagem da nova tela e marque a caixa de seleção que tem a mensagem "Entendo e aceito os riscos de segurança e privacidade ao conectar este app personalizado".
7. Clique no botão "Conectar" e aguarde a próxima tela.
8. Aparecerá uma tela chamada "Salvar app personalizado". Você pode editar o nome do app.
9. Depois de conferir se está tudo certo e a tool estar listada, clique no botão "Conectar".

> Você saberá que está tudo certo se o MCP aparecer como um novo app em "Apps personalizados para o Spark".

### Como instalar no Claude Web

1. Na barra lateral do Claude Web, clique em "Personalizar".
2. Escolha a aba "Conectores".
3. Clique no botão "Adicionar" e escolha a opção "Adicionar conector personalizado".
4. Dê um nome para o conector.
5. Cole o link do MCP (`{{URL_MCP}}`) no espaço abaixo do nome que escolheu na etapa 4.
6. Clique no botão "Adicionar".
7. Clique no botão "Vincular".
8. Clique no botão "Requer aprovação" e mude para "Sempre permitir".

### Como instalar no ChatGPT

1. Na barra lateral, clique em "Plugins".
2. Clique no botão "+", que fica do lado de "Pesquisar plugins".
3. Na tela "Novo plugin", dê um nome no espaço "Nome".
4. Em "Conexão", cole o link do MCP (`{{URL_MCP}}`) e deixe a opção "URL do Servidor" habilitada.
5. Em "Autenticação", escolha a opção "Sem autenticação" (este servidor não usa OAuth).
6. Clique na caixa de seleção "Entendi e quero continuar".
7. Clique no botão "Criar".
8. Na nova tela, clique no botão "Conectar".

## Arquitetura do código

O projeto segue Programação Orientada a Objetos, com alta coesão e baixo acoplamento.

```
mcp-dados-brasil/
├── core.py              # ClienteHTTP, Formatador, ErroConsultaExterna e a instância mcp
├── server.py             # Ponto de entrada: importa cada módulo de tools/ e expõe app
└── tools/
    ├── pix.py            # ClientePix — 3 tools
    ├── ibge.py            # ClienteIBGE — 1 tool
    ├── camara.py          # ClienteCamara — 3 tools
    ├── senado.py          # ClienteSenado — 2 tools
    ├── dou.py             # ClienteDOU — 1 tool
    └── noticias.py        # ClienteNoticias — 1 tool
```

Cada fonte de dados vira uma classe (`ClientePix`, `ClienteIBGE` etc.). A classe guarda a URL base, o cache (quando existe) e os métodos de busca e formatação daquela fonte. As funções marcadas com `@mcp.tool` são só a porta de entrada do FastMCP: cada uma valida a chamada do modelo e delega para o método correspondente da classe.

Duas regras mantêm o acoplamento baixo entre os módulos:

- Um módulo de `tools/` nunca importa de outro módulo de `tools/`. Toda peça compartilhada (cliente HTTP, formatação de número e moeda, tratamento de erro) mora em `core.py`.
- Toda chamada HTTP passa pela classe `ClienteHTTP`, de `core.py`. Ela converte qualquer falha de rede numa `ErroConsultaExterna`, com mensagem legível — nenhuma tool deixa um erro técnico cru chegar ao modelo.

Os comentários do código estão em português do Brasil, para facilitar a leitura de quem for entender ou estender o projeto.

## Créditos

Este projeto é inspirado no [mcp-brasil](https://github.com/Mcp-Brasil/mcp-brasil) (licença MIT), um servidor MCP com 70 fontes de dados públicas brasileiras e 533 tools. O mcp-dados-brasil não reaproveita código do mcp-brasil — é uma implementação própria, com escopo, arquitetura e fontes de dados diferentes. O crédito aqui reconhece a inspiração de propósito: mostrar que dado público brasileiro pode virar tool de IA.

## Licença

Distribuído sob a [licença MIT](LICENSE).

## Contato

Mário Lúcio — [LinkedIn](https://linkedin.com/in/marioluciofjr) — marioluciofjr@gmail.com — [prazocerto.me](https://prazocerto.me)
