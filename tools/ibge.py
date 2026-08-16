"""Tool de localidades do IBGE: consulta municípios e estados brasileiros
(código IBGE, UF, região), direto na API de Localidades do IBGE.

Fonte: https://servicodados.ibge.gov.br/api/docs/localidades — pública, sem chave.

Como está organizado: a classe ClienteIBGE guarda o cache da lista de
municípios como atributo de instância (em vez de variável global) e concentra
a lógica de busca. A função com @mcp.tool é só a porta de entrada do FastMCP.
"""

from __future__ import annotations

import time
import unicodedata

from mcp.types import ToolAnnotations

from core import ClienteHTTP, ErroConsultaExterna, http, mcp


class ClienteIBGE:
    """Encapsula o acesso à API de Localidades do IBGE.

    A API não filtra município por nome no servidor — por isso a classe baixa
    a lista completa (~5570 municípios) uma vez e guarda em cache por 24h como
    atributo de instância. A lista de municípios do Brasil quase nunca muda,
    então recarregar a cada consulta seria desperdício.
    """

    _BASE_URL = "https://servicodados.ibge.gov.br/api/v1/localidades"
    _TTL_CACHE_SEGUNDOS = 24 * 60 * 60

    def __init__(self, cliente_http: ClienteHTTP) -> None:
        self._http = cliente_http
        self._cache_municipios: list[dict] | None = None
        self._cache_timestamp: float = 0.0

    async def consultar(self, municipio: str | None, estado: str | None, top: int) -> str:
        """Ponto de entrada único da tool: decide se busca um estado ou uma lista de municípios."""
        top = max(1, min(top, 50))

        if estado and not municipio:
            return await self._consultar_estado(estado)

        if municipio:
            return await self._buscar_municipios(municipio, estado, top)

        return (
            "Informe pelo menos um dos parâmetros: 'municipio' (nome ou trecho do nome) "
            "ou 'estado' (sigla ou nome) para eu consultar os dados do IBGE."
        )

    async def _consultar_estado(self, estado: str) -> str:
        """Busca os dados básicos (código IBGE, região) de um único estado."""
        sigla = estado.strip().upper()
        try:
            dados = await self._http.buscar_json(f"{self._BASE_URL}/estados/{sigla}")
        except ErroConsultaExterna as exc:
            return f"Não consegui consultar o estado '{estado}': {exc}"
        if not isinstance(dados, dict) or "id" not in dados:
            return f"Estado '{estado}' não encontrado. Use a sigla (ex.: 'MG') ou o nome completo."
        return (
            f"{dados['nome']} ({dados['sigla']}) — código IBGE {dados['id']}, "
            f"região {dados['regiao']['nome']} ({dados['regiao']['sigla']})."
        )

    async def _buscar_municipios(self, municipio: str, estado: str | None, top: int) -> str:
        """Filtra, na lista completa em cache, os municípios cujo nome contém o termo buscado."""
        try:
            municipios = await self._obter_municipios()
        except ErroConsultaExterna as exc:
            return f"Não consegui consultar a lista de municípios do IBGE: {exc}"

        termo = self._normalizar(municipio.strip())
        sigla_filtro = estado.strip().upper() if estado else None
        encontrados = []
        for m in municipios:
            resumo = self._resumo_municipio(m)
            if resumo is None or termo not in self._normalizar(resumo["nome"]):
                continue
            if sigla_filtro and resumo["uf_sigla"] != sigla_filtro:
                continue
            encontrados.append(resumo)
            if len(encontrados) >= top:
                break

        if not encontrados:
            return f"Nenhum município encontrado para '{municipio}'" + (f" no estado {estado}." if estado else ".")

        linhas = [f"Municípios encontrados para '{municipio}' — {len(encontrados)} resultado(s):\n"]
        for r in encontrados:
            linhas.append(f"- {r['nome']}/{r['uf_sigla']} ({r['regiao']}) — código IBGE {r['id_ibge']}")
        linhas.append("\nFonte: IBGE — API de Localidades.")
        return "\n".join(linhas)

    async def _obter_municipios(self) -> list[dict]:
        """Devolve a lista completa de municípios do IBGE, usando o cache da instância."""
        agora = time.monotonic()
        cache_valido = self._cache_municipios is not None and (agora - self._cache_timestamp) < self._TTL_CACHE_SEGUNDOS
        if not cache_valido:
            self._cache_municipios = await self._http.buscar_json(f"{self._BASE_URL}/municipios", timeout=30.0)
            self._cache_timestamp = agora
        return self._cache_municipios or []

    @staticmethod
    def _normalizar(texto: str) -> str:
        """Remove acentos e baixa a caixa, para comparar nomes sem depender de o
        usuário digitar exatamente com os acentos corretos (ex.: 'Divinolandia' == 'Divinolândia')."""
        sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
        return sem_acento.lower()

    @staticmethod
    def _resumo_municipio(m: dict) -> dict | None:
        """Extrai só os campos relevantes de um registro de município do IBGE.

        Alguns registros (ex.: Boa Esperança do Norte/MT) vêm sem `microrregiao`
        preenchida — nesse caso, usa `regiao-imediata` como caminho alternativo até a UF.
        """
        microrregiao = m.get("microrregiao")
        if microrregiao and microrregiao.get("mesorregiao"):
            uf = microrregiao["mesorregiao"]["UF"]
        else:
            regiao_imediata = m.get("regiao-imediata") or {}
            regiao_intermediaria = regiao_imediata.get("regiao-intermediaria") or {}
            uf = regiao_intermediaria.get("UF")
        if not uf:
            return None
        return {
            "id_ibge": m["id"],
            "nome": m["nome"],
            "uf_sigla": uf["sigla"],
            "uf_nome": uf["nome"],
            "regiao": uf["regiao"]["nome"],
        }


# Instância única do cliente IBGE — o cache de municípios vive aqui, entre chamadas.
_cliente = ClienteIBGE(http)


@mcp.tool(
    name="ibge_localidades",
    annotations=ToolAnnotations(
        title="Consulta de municípios e estados (IBGE)",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def ibge_localidades(municipio: str | None = None, estado: str | None = None, top: int = 10) -> str:
    """Consulta oficial da API de Localidades do IBGE. Use esta tool sempre que a
    pergunta pedir o código IBGE, a UF, a região de um município/estado, ou quiser
    saber se existe (e onde fica) um município com determinado nome.

    Consulta o código IBGE, a UF e a região de um município, ou informações
    básicas de um estado brasileiro.

    Args:
        municipio: Nome (ou trecho do nome) do município a buscar (ex.: "Divinópolis").
        estado: Sigla (ex.: "MG") ou nome do estado. Se informado sozinho (sem
            `municipio`), devolve os dados básicos desse estado. Se informado junto
            com `municipio`, restringe a busca de município a esse estado.
        top: Quantidade máxima de municípios a devolver quando `municipio` é usado
            (padrão 10, máximo 50).
    """
    return await _cliente.consultar(municipio, estado, top)
