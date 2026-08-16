"""Tools do Pix: estatísticas públicas de transações, visão nacional e fraudes,
consultadas direto na API de Dados Abertos do Pix (Banco Central, serviço Olinda).

Fonte: https://olinda.bcb.gov.br/olinda/servico/Pix_DadosAbertos/versao/v1/documentacao
Pública, sem chave de API. Esta é a diferença deste MCP em relação ao mcp-brasil,
que não expõe esses dados (ver README, seção de créditos).

Como está organizado: a classe ClientePix concentra toda a lógica de acesso à
API do Pix (montar URL, escapar filtro, buscar e formatar). As funções com
@mcp.tool logo abaixo são só a "porta de entrada" que o FastMCP expõe ao
modelo — cada uma delega para o método correspondente da classe.
"""

from __future__ import annotations

from urllib.parse import quote

from mcp.types import ToolAnnotations

from core import ClienteHTTP, ErroConsultaExterna, Formatador, http, mcp


class ClientePix:
    """Encapsula toda a integração com a API de Dados Abertos do Pix (Banco Central).

    A API do Olinda/BCB não decodifica "+" como espaço em $orderby/$filter —
    por isso as URLs são montadas manualmente com urllib.parse.quote (que usa
    %20), em vez de depender da serialização automática de params do httpx
    (que usa "+" e faz o servidor do BCB devolver erro 400).
    """

    _BASE_URL = "https://olinda.bcb.gov.br/olinda/servico/Pix_DadosAbertos/versao/v1/odata"
    _RODAPE_FONTE = "\nFonte: Banco Central do Brasil — API de Dados Abertos do Pix (Olinda)."

    def __init__(self, cliente_http: ClienteHTTP) -> None:
        self._http = cliente_http

    # --- Métodos públicos: um por tool -------------------------------------------------

    async def transacoes_por_municipio(
        self, municipio: str | None, estado: str | None, ano_mes: int | None, top: int
    ) -> str:
        """Monta o filtro a partir dos parâmetros do usuário e devolve as
        transações Pix por município já formatadas em texto."""
        top = max(1, min(top, 100))
        filtros = []
        if municipio:
            filtros.append(f"contains(Municipio,'{self._escapar_odata(municipio.upper())}')")
        if estado:
            filtros.append(f"Estado eq '{self._escapar_odata(estado.upper())}'")
        if ano_mes:
            filtros.append(f"AnoMes eq {int(ano_mes)}")
        filtro = " and ".join(filtros) if filtros else None

        url = self._montar_url_odata(
            "TransacoesPixPorMunicipio",
            "DataBase",
            filtro=filtro,
            top=top,
            select=(
                "AnoMes,Municipio,Estado,Regiao,VL_PagadorPF,QT_PagadorPF,"
                "VL_PagadorPJ,QT_PagadorPJ,VL_RecebedorPF,QT_RecebedorPF,"
                "VL_RecebedorPJ,QT_RecebedorPJ"
            ),
        )

        try:
            dados = await self._http.buscar_json(url)
        except ErroConsultaExterna as exc:
            return f"Não consegui consultar as transações Pix por município: {exc}"

        registros = dados.get("value", [])
        if not registros:
            return (
                "Nenhum registro encontrado para os filtros informados "
                f"(município={municipio!r}, estado={estado!r}, ano_mes={ano_mes!r})."
            )

        linhas = [f"Transações Pix por município — {len(registros)} registro(s) encontrado(s):\n"]
        for r in registros:
            linhas.append(
                f"- {r['Municipio']}/{r['Estado']} ({r['Regiao']}), {r['AnoMes']}:\n"
                f"  Pago por PF: {Formatador.moeda(r['VL_PagadorPF'])} em {Formatador.numero(r['QT_PagadorPF'])} transações\n"
                f"  Pago por PJ: {Formatador.moeda(r['VL_PagadorPJ'])} em {Formatador.numero(r['QT_PagadorPJ'])} transações\n"
                f"  Recebido por PF: {Formatador.moeda(r['VL_RecebedorPF'])} em {Formatador.numero(r['QT_RecebedorPF'])} transações\n"
                f"  Recebido por PJ: {Formatador.moeda(r['VL_RecebedorPJ'])} em {Formatador.numero(r['QT_RecebedorPJ'])} transações"
            )
        linhas.append(self._RODAPE_FONTE)
        return "\n".join(linhas)

    async def estatisticas_nacionais(
        self, ano_mes: int | None, pagador: str | None, recebedor: str | None, top: int
    ) -> str:
        """Devolve a visão agregada nacional do Pix, cruzando perfil de pagador
        e recebedor, região, faixa etária, forma de iniciação e finalidade."""
        top = max(1, min(top, 100))
        filtros = []
        if ano_mes:
            filtros.append(f"AnoMes eq {int(ano_mes)}")
        if pagador:
            filtros.append(f"PAG_PFPJ eq '{self._escapar_odata(pagador.upper())}'")
        if recebedor:
            filtros.append(f"REC_PFPJ eq '{self._escapar_odata(recebedor.upper())}'")
        filtro = " and ".join(filtros) if filtros else None

        url = self._montar_url_odata("EstatisticasTransacoesPix", "Database", filtro=filtro, top=top)

        try:
            # Esta entidade da API do BCB costuma responder mais devagar que as outras.
            dados = await self._http.buscar_json(url, timeout=45.0)
        except ErroConsultaExterna as exc:
            return f"Não consegui consultar as estatísticas nacionais do Pix: {exc}"

        registros = dados.get("value", [])
        if not registros:
            return (
                "Nenhum registro encontrado para os filtros informados "
                f"(ano_mes={ano_mes!r}, pagador={pagador!r}, recebedor={recebedor!r})."
            )

        linhas = [f"Estatísticas nacionais do Pix — {len(registros)} registro(s) encontrado(s):\n"]
        for r in registros:
            linhas.append(
                f"- {r['AnoMes']}: {r['PAG_PFPJ']} pagando {r['REC_PFPJ']}, "
                f"pagador na região {r['PAG_REGIAO']} (faixa {r['PAG_IDADE']}), "
                f"recebedor na região {r['REC_REGIAO']} (faixa {r['REC_IDADE']}), "
                f"via {r['FORMAINICIACAO']}, natureza {r['NATUREZA']}, finalidade {r['FINALIDADE']}: "
                f"{Formatador.moeda(r['VALOR'])} em {Formatador.numero(r['QUANTIDADE'])} transações"
            )
        linhas.append(self._RODAPE_FONTE)
        return "\n".join(linhas)

    async def fraudes_contestacoes(self, ano_mes: int | None, top: int) -> str:
        """Devolve os dados mensais de contestações, fraudes e devoluções via MED do Pix."""
        top = max(1, min(top, 60))
        filtro = f"AnoMes eq {int(ano_mes)}" if ano_mes else None

        url = self._montar_url_odata("EstatisticasFraudesPix", "Database", filtro=filtro, top=top)

        try:
            # Esta entidade da API do BCB costuma responder mais devagar que as outras.
            dados = await self._http.buscar_json(url, timeout=45.0)
        except ErroConsultaExterna as exc:
            return f"Não consegui consultar os dados de fraudes e contestações do Pix: {exc}"

        registros = dados.get("value", [])
        if not registros:
            return f"Nenhum registro encontrado para o período informado (ano_mes={ano_mes!r})."

        linhas = [f"Fraudes e contestações do Pix — {len(registros)} mês(es) encontrado(s):\n"]
        for r in registros:
            linhas.append(
                f"- {r['AnoMes']}:\n"
                f"  Pix contestados: {Formatador.numero(int(r['QtdePixcontestados']))}\n"
                f"  Contestações aceitas: {Formatador.numero(int(r['Qtdecontestacoesaceitas']))} "
                f"| rejeitadas: {Formatador.numero(int(r['Qtdecontestacoesrejeitadas']))}\n"
                f"  Valor contestado aceito: {Formatador.moeda(r['ValorPixcontestadosaceitos'])}\n"
                f"  Devolvido integralmente (MED): {Formatador.moeda(r['ValorPixdevolvidosintegralmente'])}\n"
                f"  Devolvido parcialmente (MED): {Formatador.moeda(r['ValorPixdevolvidosparcialmente'])}\n"
                f"  Valor residual não devolvido: {Formatador.moeda(r['ValorPixresidualnaodevolvido'])}"
            )
        linhas.append(self._RODAPE_FONTE)
        return "\n".join(linhas)

    # --- Métodos privados: detalhe de implementação da API OData -----------------------

    def _montar_url_odata(
        self,
        entidade: str,
        parametro_data: str,
        *,
        filtro: str | None = None,
        select: str | None = None,
        top: int = 50,
        orderby: str = "AnoMes desc",
    ) -> str:
        """Monta a URL de uma consulta OData da API do Pix, com o parâmetro de data em branco.

        O parâmetro de data (`DataBase` ou `Database`, dependendo da entidade) fica
        sempre em branco (`''`) porque as entidades desta API já devolvem o histórico
        completo — o recorte por período é feito via `$filter` em `AnoMes`, não pelo
        parâmetro de data.
        """
        partes = [
            f"@{parametro_data}={quote(chr(39) + chr(39))}",
            "$format=json",
            f"$top={top}",
            f"$orderby={quote(orderby)}",
        ]
        if filtro:
            partes.append(f"$filter={quote(filtro)}")
        if select:
            partes.append(f"$select={quote(select)}")
        query = "&".join(partes)
        return f"{self._BASE_URL}/{entidade}({parametro_data}=@{parametro_data})?{query}"

    @staticmethod
    def _escapar_odata(valor: str) -> str:
        """Escapa aspas simples de um valor de texto para uso seguro dentro de um $filter OData."""
        return valor.replace("'", "''")


# Instância única do cliente Pix, compartilhada pelas 3 tools deste módulo.
_cliente = ClientePix(http)


@mcp.tool(
    name="pix_transacoes_por_municipio",
    annotations=ToolAnnotations(
        title="Transações Pix por município",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def pix_transacoes_por_municipio(
    municipio: str | None = None,
    estado: str | None = None,
    ano_mes: int | None = None,
    top: int = 12,
) -> str:
    """Estatísticas de transações Pix por município: valores e quantidades pagas e
    recebidas por pessoa física (PF) e jurídica (PJ), com o município, estado e região.

    Args:
        municipio: Nome do município (busca por trecho, sem acento importa pouco pois
            a base já vem em maiúsculas — ex.: "BELO HORIZONTE").
        estado: Nome do estado por extenso, em maiúsculas (ex.: "MINAS GERAIS").
        ano_mes: Período no formato AAAAMM (ex.: 202607 para julho de 2026). Se
            omitido, devolve os períodos mais recentes disponíveis.
        top: Quantidade máxima de registros a devolver (padrão 12, máximo 100).
    """
    return await _cliente.transacoes_por_municipio(municipio, estado, ano_mes, top)


@mcp.tool(
    name="pix_estatisticas_nacionais",
    annotations=ToolAnnotations(
        title="Estatísticas nacionais do Pix",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def pix_estatisticas_nacionais(
    ano_mes: int | None = None,
    pagador: str | None = None,
    recebedor: str | None = None,
    top: int = 20,
) -> str:
    """Visão agregada nacional do Pix: valor e quantidade de transações, cruzando
    perfil de pagador/recebedor (PF ou PJ), região, faixa etária, forma de
    iniciação (ex.: DICT, QR Code) e finalidade (ex.: Pix, Saque, Troco).

    Args:
        ano_mes: Período no formato AAAAMM (ex.: 202607). Se omitido, devolve os
            períodos mais recentes disponíveis.
        pagador: Perfil do pagador — "PF" ou "PJ". Opcional.
        recebedor: Perfil do recebedor — "PF" ou "PJ". Opcional.
        top: Quantidade máxima de registros a devolver (padrão 20, máximo 100).
    """
    return await _cliente.estatisticas_nacionais(ano_mes, pagador, recebedor, top)


@mcp.tool(
    name="pix_fraudes_contestacoes",
    annotations=ToolAnnotations(
        title="Fraudes e contestações do Pix",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def pix_fraudes_contestacoes(ano_mes: int | None = None, top: int = 12) -> str:
    """Dados de contestações e fraudes do Pix por mês: quantidade de Pix contestados,
    contestações aceitas/rejeitadas, valores devolvidos (integral e parcialmente)
    via MED (Mecanismo Especial de Devolução) e valor residual não devolvido.

    Args:
        ano_mes: Período no formato AAAAMM (ex.: 202607). Se omitido, devolve os
            períodos mais recentes disponíveis.
        top: Quantidade máxima de meses a devolver (padrão 12, máximo 60).
    """
    return await _cliente.fraudes_contestacoes(ano_mes, top)
