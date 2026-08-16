"""Núcleo compartilhado do mcp-dados-brasil.

Este módulo é a única "porta de entrada" comum que os módulos de tools/ podem
usar. Ele guarda:
- `mcp`: a instância única do servidor MCP, onde cada módulo registra suas tools.
- `ClienteHTTP`: uma classe que faz as chamadas HTTP e trata erro de forma
  padronizada, para nenhum módulo de tools/ precisar repetir esse código.
- `Formatador`: uma classe com métodos estáticos para formatar número e
  dinheiro no padrão brasileiro.
- `ErroConsultaExterna`: a exceção que toda tool usa para avisar, de forma
  amigável, que uma fonte de dados externa falhou.

Cada módulo de tools/ importa só o que precisa daqui — nunca importa de outro
módulo de tools/. Essa regra mantém baixo acoplamento entre as fontes de dados.
"""

from __future__ import annotations

import httpx
from fastmcp import FastMCP

# `instructions` vai no handshake inicial do protocolo MCP e é o principal sinal
# que um cliente (Gemini Spark, Claude, ChatGPT) tem para decidir, sozinho, se
# chama uma tool deste servidor — mesmo quando a pessoa usuária não cita o nome
# do app no prompt. Por isso o texto é explícito sobre QUANDO usar cada tool,
# não só sobre o que o servidor é.
_INSTRUCOES_SERVIDOR = (
    "Servidor de dados abertos e públicos do governo brasileiro, só leitura, sem "
    "chave de API. Use estas tools sempre que a pergunta envolver: estatísticas de "
    "transações Pix (Banco Central); código IBGE, UF ou região de um município ou "
    "estado; deputados federais, suas votações ou despesas (CEAP); senadores "
    "federais ou as matérias legislativas deles; busca de termo no Diário Oficial "
    "da União; ou últimas notícias por editoria via Agência Brasil. Chame uma "
    "tool sempre que o pedido casar com um desses temas, mesmo que a pessoa não "
    "mencione o nome deste servidor ou peça explicitamente para 'usar o MCP'."
)

# Instância única do servidor MCP, compartilhada por todos os módulos de tools/.
# Cada módulo usa o decorador @mcp.tool desta mesma instância para registrar
# suas tools — é isso que junta tudo num só servidor na hora do deploy.
mcp = FastMCP("DadosBrasil", instructions=_INSTRUCOES_SERVIDOR)


class ErroConsultaExterna(Exception):
    """Erro ao consultar uma fonte de dados externa (HTTP, timeout, formato inesperado).

    Toda tool captura essa exceção e devolve uma mensagem amigável ao modelo,
    em vez de deixar um erro técnico cru (stack trace, timeout de rede) vazar.
    """


class ClienteHTTP:
    """Cliente HTTP assíncrono com tratamento de erro centralizado.

    Todas as tools do projeto passam por aqui para fazer uma requisição —
    assim, o tratamento de timeout e de erro HTTP fica escrito uma única vez,
    em vez de repetido em cada um dos 6 módulos de tools/.
    """

    def __init__(self, timeout_padrao: float = 30.0) -> None:
        self._timeout_padrao = timeout_padrao

    async def buscar_json(
        self,
        url: str,
        *,
        params: dict | None = None,
        headers: dict | None = None,
        timeout: float | None = None,
    ) -> dict | list:
        """Faz um GET assíncrono e devolve o corpo já decodificado como JSON."""
        corpo = await self._get(url, params=params, headers=headers, timeout=timeout)
        return corpo.json()

    async def buscar_texto(
        self,
        url: str,
        *,
        params: dict | None = None,
        headers: dict | None = None,
        timeout: float | None = None,
    ) -> str:
        """Faz um GET assíncrono e devolve o corpo como texto puro (usado para RSS/XML/HTML)."""
        corpo = await self._get(url, params=params, headers=headers, timeout=timeout)
        return corpo.text

    async def buscar_bytes(
        self,
        url: str,
        *,
        params: dict | None = None,
        headers: dict | None = None,
        timeout: float | None = None,
    ) -> bytes:
        """Faz um GET assíncrono e devolve o corpo cru em bytes (usado para arquivo
        compactado, como o CSV de despesas da Câmara em .zip)."""
        corpo = await self._get(url, params=params, headers=headers, timeout=timeout)
        return corpo.content

    async def _get(
        self,
        url: str,
        *,
        params: dict | None,
        headers: dict | None,
        timeout: float | None,
    ) -> httpx.Response:
        """Executa o GET de fato. Converte qualquer falha de rede numa ErroConsultaExterna,
        para as tools nunca precisarem tratar exceção do httpx diretamente."""
        try:
            async with httpx.AsyncClient(timeout=timeout or self._timeout_padrao) as sessao:
                resposta = await sessao.get(url, params=params, headers=headers)
                resposta.raise_for_status()
                return resposta
        except httpx.TimeoutException as exc:
            raise ErroConsultaExterna(f"A fonte de dados não respondeu a tempo ({url}).") from exc
        except httpx.HTTPStatusError as exc:
            raise ErroConsultaExterna(
                f"A fonte de dados devolveu erro HTTP {exc.response.status_code} ({url})."
            ) from exc
        except httpx.HTTPError as exc:
            raise ErroConsultaExterna(f"Falha ao consultar a fonte de dados ({url}): {exc}.") from exc


class Formatador:
    """Formata número e dinheiro no padrão brasileiro (separador de milhar com
    ponto, decimal com vírgula). Métodos estáticos porque não guardam estado —
    são só funções de conversão, agrupadas aqui por assunto."""

    @staticmethod
    def moeda(valor: float) -> str:
        """Formata um número em reais no padrão brasileiro (R$ 1.234.567,89)."""
        texto = f"{valor:,.2f}"
        texto = texto.replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
        return f"R$ {texto}"

    @staticmethod
    def numero(valor: int) -> str:
        """Formata um número inteiro no padrão brasileiro (1.234.567)."""
        return f"{valor:,}".replace(",", ".")


# Instância única do cliente HTTP, compartilhada por todos os módulos de tools/
# — evita que cada módulo crie seu próprio cliente com sua própria configuração.
http = ClienteHTTP()
