"""Tool de notícias: últimas notícias por editoria via RSS da Agência Brasil (EBC),
agência pública de notícias, sem chave de API.

Fonte: https://agenciabrasil.ebc.com.br/rss/{editoria}/feed.xml

Como está organizado: a classe ClienteNoticias concentra a lógica de buscar e
interpretar o feed RSS. A função com @mcp.tool é só a porta de entrada do FastMCP.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from html import unescape

from mcp.types import ToolAnnotations

from core import ClienteHTTP, ErroConsultaExterna, http, mcp


class ClienteNoticias:
    """Encapsula a leitura dos feeds RSS de notícias da Agência Brasil (EBC)."""

    _URL_FEED = "https://agenciabrasil.ebc.com.br/rss/{editoria}/feed.xml"
    _CABECALHOS = {"User-Agent": "Mozilla/5.0 (compatible; mcp-dados-brasil/1.0)"}
    _PADRAO_TAG_HTML = re.compile(r"<[^>]+>")
    _EDITORIAS = {
        "geral",
        "politica",
        "economia",
        "justica",
        "educacao",
        "saude",
        "internacional",
        "esportes",
        "direitos-humanos",
    }

    def __init__(self, cliente_http: ClienteHTTP) -> None:
        self._http = cliente_http

    async def ultimas_por_editoria(self, editoria: str, top: int) -> str:
        """Valida a editoria, busca o feed RSS correspondente e devolve as notícias formatadas."""
        editoria = editoria.strip().lower()
        if editoria not in self._EDITORIAS:
            opcoes = ", ".join(sorted(self._EDITORIAS))
            return f"Editoria '{editoria}' inválida. Use uma destas: {opcoes}."

        top = max(1, min(top, 20))
        url = self._URL_FEED.format(editoria=editoria)

        try:
            corpo_xml = await self._http.buscar_texto(url, headers=self._CABECALHOS, timeout=20.0)
        except ErroConsultaExterna as exc:
            return f"Não consegui consultar o feed de notícias da Agência Brasil: {exc}"

        try:
            raiz = ET.fromstring(corpo_xml)
        except ET.ParseError as exc:
            return f"O feed de notícias da Agência Brasil veio num formato inesperado: {exc}"

        itens = raiz.findall(".//item")[:top]
        if not itens:
            return f"Nenhuma notícia encontrada na editoria '{editoria}' no momento."

        linhas = [f"Últimas notícias — editoria '{editoria}' — {len(itens)} resultado(s):\n"]
        for item in itens:
            titulo = (item.findtext("title") or "sem título").strip()
            link = (item.findtext("link") or "").strip()
            data_publicacao = (item.findtext("pubDate") or "").strip()
            resumo = self._limpar_html(item.findtext("description"))[:200]
            linhas.append(f"- {titulo} ({data_publicacao})\n  {resumo}...\n  {link}")
        linhas.append("\nFonte: Agência Brasil — EBC (Empresa Brasil de Comunicação).")
        return "\n".join(linhas)

    @classmethod
    def _limpar_html(cls, texto: str | None) -> str:
        """Remove tags HTML e decodifica entidades de um trecho de descrição do RSS."""
        return unescape(cls._PADRAO_TAG_HTML.sub(" ", texto or "")).strip()


# Instância única do cliente de notícias, compartilhada pela tool deste módulo.
_cliente = ClienteNoticias(http)


@mcp.tool(
    name="noticias_agencia_brasil",
    annotations=ToolAnnotations(
        title="Últimas notícias (Agência Brasil)",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def noticias_agencia_brasil(editoria: str = "geral", top: int = 10) -> str:
    """Feed oficial da Agência Brasil (EBC), agência pública de notícias. Use esta
    tool sempre que a pergunta pedir as notícias mais recentes do Brasil por
    assunto — não faz busca por palavra-chave, só filtra por editoria.

    Últimas notícias publicadas pela Agência Brasil (EBC), agência pública de
    notícias, filtradas por editoria.

    Args:
        editoria: Uma das editorias disponíveis: "geral", "politica", "economia",
            "justica", "educacao", "saude", "internacional", "esportes" ou
            "direitos-humanos". Padrão "geral".
        top: Quantidade máxima de notícias a devolver (padrão 10, máximo 20 —
            o feed da Agência Brasil não publica mais que isso por vez).
    """
    return await _cliente.ultimas_por_editoria(editoria, top)
