"""Tool do Diário Oficial da União: busca de termo nas edições do DOU.

A API oficial da Imprensa Nacional (WS-INCom) é restrita a órgãos de governo,
e o INLABS (arquivos XML completos) exige cadastro de login — nenhuma delas
serve para este MCP, que só usa fontes sem chave/login. Por isso esta tool
consulta o mesmo mecanismo de busca que a página pública
https://www.in.gov.br/consulta usa: a página devolve os resultados já prontos
num bloco `<script type="application/json">` embutido no HTML (não é uma API
documentada oficialmente), então a tool segue o padrão de "scraping
resiliente" do projeto: cache curto e checagem de formato antes de devolver.

Como está organizado: a classe ClienteDOU guarda o cache de buscas recentes
como atributo de instância e concentra a lógica de raspagem. A função com
@mcp.tool é só a porta de entrada do FastMCP.
"""

from __future__ import annotations

import json
import re
import time
from html import unescape

from mcp.types import ToolAnnotations

from core import ClienteHTTP, ErroConsultaExterna, http, mcp


class ClienteDOU:
    """Encapsula a busca pública no Diário Oficial da União (in.gov.br/consulta)."""

    _URL_BUSCA = "https://www.in.gov.br/consulta/-/buscar/dou"
    _URL_ARTIGO = "https://www.in.gov.br/web/dou/-/{url_title}"
    _CABECALHOS = {"User-Agent": "Mozilla/5.0 (compatible; mcp-dados-brasil/1.0)"}
    _SECOES = {"1": "do1", "2": "do2", "3": "do3", "edital": "doe"}
    _TTL_CACHE_SEGUNDOS = 10 * 60

    # O bloco de resultados vem embutido neste <script> específico da página de busca.
    _PADRAO_BLOCO_JSON = re.compile(
        r'<script id="_br_com_seatecnologia_in_buscadou_BuscaDouPortlet_params" type="application/json">\s*(\{.*?\})\s*</script>',
        re.DOTALL,
    )
    _PADRAO_TAG_HTML = re.compile(r"<[^>]+>")

    def __init__(self, cliente_http: ClienteHTTP) -> None:
        self._http = cliente_http
        self._cache: dict[tuple, tuple[float, list[dict]]] = {}

    async def buscar_termo(self, termo: str, secao: str | None, periodo: str, top: int) -> str:
        """Valida os parâmetros, busca no DOU e devolve os resultados formatados."""
        top = max(1, min(top, 30))
        if periodo not in {"dia", "semana", "mes", "ano"}:
            return "O parâmetro 'periodo' deve ser um destes: 'dia', 'semana', 'mes' ou 'ano'."

        secao_codigo = self._SECOES.get(secao.strip()) if secao else None
        if secao and not secao_codigo:
            return "O parâmetro 'secao' deve ser '1', '2', '3' ou 'edital'."

        try:
            resultados = await self._buscar_resultados(termo, secao_codigo, periodo)
        except ErroConsultaExterna as exc:
            return f"Não consegui buscar no Diário Oficial da União: {exc}"

        if not resultados:
            return f"Nenhum resultado encontrado para '{termo}' no período informado ({periodo})."

        resultados = resultados[:top]
        linhas = [f"Diário Oficial da União — {len(resultados)} resultado(s) para '{termo}':\n"]
        for r in resultados:
            titulo = self._limpar_html(r.get("title", "sem título"))
            trecho = self._limpar_html(r.get("content", ""))[:220]
            url_artigo = self._URL_ARTIGO.format(url_title=r.get("urlTitle", ""))
            linhas.append(
                f"- {titulo} ({r.get('pubName', '?')}, edição {r.get('editionNumber', '?')}, {r.get('pubDate', '?')})\n"
                f"  \"...{trecho}...\"\n"
                f"  {url_artigo}"
            )
        linhas.append("\nFonte: Imprensa Nacional — busca pública do Diário Oficial da União (in.gov.br/consulta).")
        return "\n".join(linhas)

    async def _buscar_resultados(self, termo: str, secao: str | None, periodo: str) -> list[dict]:
        """Consulta a busca pública do DOU, usando um cache curto por (termo, seção, período)."""
        chave_cache = (termo, secao, periodo)
        agora = time.monotonic()
        em_cache = self._cache.get(chave_cache)
        if em_cache and (agora - em_cache[0]) < self._TTL_CACHE_SEGUNDOS:
            return em_cache[1]

        params: dict[str, str] = {"q": termo, "exactDate": periodo}
        if secao:
            params["s"] = secao

        corpo_html = await self._http.buscar_texto(self._URL_BUSCA, params=params, headers=self._CABECALHOS, timeout=25.0)
        correspondencia = self._PADRAO_BLOCO_JSON.search(corpo_html)
        if not correspondencia:
            # A página do in.gov.br pode mudar de estrutura sem aviso — se o bloco
            # esperado não aparecer, é melhor avisar do que arriscar devolver nada.
            raise ErroConsultaExterna(
                "A página de busca do Diário Oficial da União mudou de formato e não consegui "
                "extrair os resultados. Tente novamente mais tarde ou busque direto em in.gov.br/consulta."
            )

        bloco = json.loads(correspondencia.group(1))
        resultados = bloco.get("jsonArray") or []
        self._cache[chave_cache] = (agora, resultados)
        return resultados

    @classmethod
    def _limpar_html(cls, texto: str) -> str:
        """Remove tags HTML (ex.: <span class='highlight'>) e decodifica entidades."""
        return unescape(cls._PADRAO_TAG_HTML.sub("", texto)).strip()


# Instância única do cliente do DOU — o cache de buscas recentes vive aqui, entre chamadas.
_cliente = ClienteDOU(http)


@mcp.tool(
    name="dou_buscar_termo",
    annotations=ToolAnnotations(
        title="Busca no Diário Oficial da União",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def dou_buscar_termo(termo: str, secao: str | None = None, periodo: str = "mes", top: int = 10) -> str:
    """Consulta oficial (busca pública) do Diário Oficial da União, mantida pela
    Imprensa Nacional. Use esta tool sempre que a pergunta pedir para verificar se
    algo foi publicado oficialmente pelo governo federal — portaria, edital,
    nomeação, decisão, concurso — inclusive para o período mais recente.

    Busca um termo em edições do Diário Oficial da União (DOU).

    Args:
        termo: Palavra ou expressão a buscar (ex.: "nomeação", "concurso público").
        secao: Seção do DOU a filtrar — "1" (atos normativos), "2" (atos de
            pessoal) ou "3" (contratos/licitações). Se omitido, busca em todas.
        periodo: Janela de tempo da busca — "dia", "semana", "mes" ou "ano".
            Padrão "mes" (últimos 30 dias).
        top: Quantidade máxima de resultados (padrão 10, máximo 30).
    """
    return await _cliente.buscar_termo(termo, secao, periodo, top)
