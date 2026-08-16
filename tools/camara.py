"""Tools da Câmara dos Deputados: busca de deputados, votações de uma proposição
(com os votos individuais quando há registro nominal) e despesas parlamentares (CEAP).

Fonte: https://dadosabertos.camara.leg.br/swagger/api.html — pública, sem chave.

Como está organizado: a classe ClienteCamara concentra toda a lógica de acesso
à API da Câmara. As funções com @mcp.tool são só a porta de entrada do FastMCP,
cada uma delegando para o método correspondente da classe.
"""

from __future__ import annotations

import csv
import io
import time
import zipfile
from collections import defaultdict
from datetime import date

from mcp.types import ToolAnnotations

from core import ClienteHTTP, ErroConsultaExterna, Formatador, http, mcp

_RODAPE_FONTE = "\nFonte: Câmara dos Deputados — API de Dados Abertos."


class ClienteCamara:
    """Encapsula toda a integração com a API de Dados Abertos da Câmara dos Deputados."""

    _BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"

    # O endpoint /deputados/{id}/despesas da API JSON está com o backend fora do
    # ar: toda resposta vem com "dados": [] e o cabeçalho HTTP `retry-after` fixo,
    # mesmo para combinações de deputado/ano historicamente conhecidas por terem
    # despesa registrada — sinal de um circuit breaker devolvendo uma resposta
    # sintética, não de falta de dado real. Por isso as despesas vêm do arquivo
    # CSV oficial que a própria Câmara publica por ano (mesmo dado, fonte diferente).
    _URL_CSV_DESPESAS = "https://www.camara.leg.br/cotas/Ano-{ano}.csv.zip"
    _TTL_CACHE_DESPESAS_SEGUNDOS = 6 * 60 * 60

    def __init__(self, cliente_http: ClienteHTTP) -> None:
        self._http = cliente_http
        self._cache_despesas: dict[int, tuple[float, dict[str, list[dict]]]] = {}

    async def buscar_deputados(self, nome: str | None, estado: str | None, partido: str | None, top: int) -> str:
        """Busca deputados por nome, UF e/ou partido e devolve a lista formatada."""
        top = max(1, min(top, 50))
        params: dict[str, str | int] = {"itens": top, "ordem": "ASC", "ordenarPor": "nome"}
        if nome:
            params["nome"] = nome
        if estado:
            params["siglaUf"] = estado.strip().upper()
        if partido:
            params["siglaPartido"] = partido.strip().upper()

        try:
            dados = await self._http.buscar_json(f"{self._BASE_URL}/deputados", params=params)
        except ErroConsultaExterna as exc:
            return f"Não consegui consultar os deputados: {exc}"

        registros = dados.get("dados", [])
        if not registros:
            return "Nenhum deputado encontrado para os filtros informados."

        linhas = [f"Deputados encontrados — {len(registros)} resultado(s):\n"]
        for d in registros:
            linhas.append(f"- {d['nome']} ({d['siglaPartido']}/{d['siglaUf']}) — id {d['id']}, e-mail {d.get('email') or 'não informado'}")
        linhas.append(_RODAPE_FONTE)
        return "\n".join(linhas)

    async def consultar_votacoes(
        self,
        sigla_tipo: str | None,
        numero: int | None,
        ano: int | None,
        id_votacao: str | None,
        top: int,
    ) -> str:
        """Ponto de entrada único da tool de votações: decide entre listar votos
        individuais de uma votação específica ou listar as votações de uma proposição."""
        top = max(1, min(top, 30))

        if id_votacao:
            return await self._votos_de_uma_votacao(id_votacao)

        if not (sigla_tipo and numero and ano):
            return "Informe 'sigla_tipo', 'numero' e 'ano' da proposição (ex.: PL, 1800, 2023), ou um 'id_votacao' específico."

        return await self._votacoes_de_uma_proposicao(sigla_tipo, numero, ano, top)

    async def _votos_de_uma_votacao(self, id_votacao: str) -> str:
        """Lista o voto de cada deputado numa votação nominal específica."""
        try:
            dados = await self._http.buscar_json(f"{self._BASE_URL}/votacoes/{id_votacao}/votos")
        except ErroConsultaExterna as exc:
            return f"Não consegui consultar os votos da votação {id_votacao}: {exc}"

        votos = dados.get("dados", [])
        if not votos:
            return (
                f"A votação {id_votacao} não tem votos individuais registrados "
                "(provavelmente foi uma votação simbólica, sem chamada nominal)."
            )

        linhas = [f"Votos da votação {id_votacao} — {len(votos)} registrado(s):\n"]
        for v in votos:
            dep = v.get("deputado_", {})
            linhas.append(f"- {dep.get('nome', '?')} ({dep.get('siglaPartido', '?')}/{dep.get('siglaUf', '?')}): {v.get('tipoVoto', '?')}")
        linhas.append(_RODAPE_FONTE)
        return "\n".join(linhas)

    async def _votacoes_de_uma_proposicao(self, sigla_tipo: str, numero: int, ano: int, top: int) -> str:
        """Localiza a proposição pelo tipo/número/ano e lista suas votações."""
        try:
            proposicoes = await self._http.buscar_json(
                f"{self._BASE_URL}/proposicoes",
                params={"siglaTipo": sigla_tipo.strip().upper(), "numero": numero, "ano": ano, "itens": 1},
            )
        except ErroConsultaExterna as exc:
            return f"Não consegui localizar a proposição: {exc}"

        encontradas = proposicoes.get("dados", [])
        if not encontradas:
            return f"Nenhuma proposição encontrada para {sigla_tipo.upper()} {numero}/{ano}."
        id_proposicao = encontradas[0]["id"]

        try:
            dados = await self._http.buscar_json(f"{self._BASE_URL}/votacoes", params={"idProposicao": id_proposicao, "itens": top})
        except ErroConsultaExterna as exc:
            return f"Não consegui consultar as votações da proposição: {exc}"

        votacoes = dados.get("dados", [])
        if not votacoes:
            return f"A proposição {sigla_tipo.upper()} {numero}/{ano} ainda não teve nenhuma votação registrada."

        linhas = [f"Votações de {sigla_tipo.upper()} {numero}/{ano} — {len(votacoes)} registrada(s):\n"]
        for v in votacoes:
            resultado = "aprovada" if v.get("aprovacao") == 1 else "rejeitada" if v.get("aprovacao") == 0 else "sem resultado registrado"
            linhas.append(f"- {v['data']} ({v['siglaOrgao']}), id {v['id']}: {v['descricao']} — {resultado}")
        linhas.append(_RODAPE_FONTE)
        return "\n".join(linhas)

    async def despesas_deputado(self, id_deputado: int | None, nome: str | None, ano: int | None, mes: int | None, top: int) -> str:
        """Resolve o id do deputado (por nome, se preciso) e devolve as despesas CEAP dele,
        lidas do arquivo CSV oficial anual (ver nota em `_URL_CSV_DESPESAS`)."""
        top = max(1, min(top, 100))

        if not id_deputado:
            if not nome:
                return "Informe 'id_deputado' ou 'nome' do deputado para eu consultar as despesas."
            id_deputado_ou_erro = await self._resolver_id_por_nome(nome)
            if isinstance(id_deputado_ou_erro, str):
                return id_deputado_ou_erro  # já é a mensagem de erro/ambiguidade pronta
            id_deputado = id_deputado_ou_erro

        ano_consulta = ano or date.today().year
        try:
            despesas_por_deputado = await self._obter_despesas_do_ano(ano_consulta)
        except ErroConsultaExterna as exc:
            return f"Não consegui baixar o arquivo de despesas de {ano_consulta}: {exc}"

        linhas_deputado = despesas_por_deputado.get(str(id_deputado), [])
        if mes:
            linhas_deputado = [linha for linha in linhas_deputado if linha.get("numMes") == str(mes)]

        if not linhas_deputado:
            return f"Nenhuma despesa encontrada para o deputado id {id_deputado}{self._descrever_periodo(ano_consulta, mes)}."

        linhas_deputado.sort(key=lambda linha: linha.get("datEmissao", ""), reverse=True)
        total = sum(self._valor_liquido(linha) for linha in linhas_deputado)
        selecionadas = linhas_deputado[:top]

        linhas = [
            f"Despesas do deputado id {id_deputado} em {ano_consulta}"
            f"{f'/{mes:02d}' if mes else ''} — {len(linhas_deputado)} registro(s), "
            f"total {Formatador.moeda(total)} (mostrando os {len(selecionadas)} mais recentes):\n"
        ]
        for linha in selecionadas:
            data = linha.get("datEmissao", "?").split("T")[0]
            linhas.append(
                f"- {data} | {linha.get('txtDescricao', '?')} | {linha.get('txtFornecedor', '?')}: "
                f"{Formatador.moeda(self._valor_liquido(linha))}"
            )
        linhas.append("\nFonte: Câmara dos Deputados — arquivo oficial de despesas CEAP (camara.leg.br/cotas).")
        return "\n".join(linhas)

    async def _obter_despesas_do_ano(self, ano: int) -> dict[str, list[dict]]:
        """Baixa e agrupa por deputado (`ideCadastro`) o arquivo CSV oficial de
        despesas CEAP do ano informado. Cache de 6h por ano, para não baixar de
        novo o arquivo inteiro (dezenas de MB descompactado) a cada consulta."""
        agora = time.monotonic()
        em_cache = self._cache_despesas.get(ano)
        if em_cache and (agora - em_cache[0]) < self._TTL_CACHE_DESPESAS_SEGUNDOS:
            return em_cache[1]

        url = self._URL_CSV_DESPESAS.format(ano=ano)
        conteudo_zip = await self._http.buscar_bytes(url, timeout=45.0)

        agrupado: dict[str, list[dict]] = defaultdict(list)
        with zipfile.ZipFile(io.BytesIO(conteudo_zip)) as arquivo:
            texto_csv = arquivo.read(arquivo.namelist()[0]).decode("utf-8-sig")
        for linha in csv.DictReader(io.StringIO(texto_csv), delimiter=";"):
            id_deputado = linha.get("ideCadastro")
            if id_deputado:
                agrupado[id_deputado].append(linha)

        resultado = dict(agrupado)
        self._cache_despesas[ano] = (agora, resultado)
        return resultado

    @staticmethod
    def _valor_liquido(linha: dict) -> float:
        """Converte o campo `vlrLiquido` do CSV (string, ex.: '168.85') em float."""
        try:
            return float(linha.get("vlrLiquido") or 0)
        except ValueError:
            return 0.0

    async def _resolver_id_por_nome(self, nome: str) -> int | str:
        """Busca o deputado pelo nome. Devolve o id se achar só 1 resultado, ou
        uma mensagem pronta (erro ou lista de opções) se achar 0 ou mais de 1."""
        try:
            busca = await self._http.buscar_json(f"{self._BASE_URL}/deputados", params={"nome": nome, "itens": 5})
        except ErroConsultaExterna as exc:
            return f"Não consegui localizar o deputado '{nome}': {exc}"
        candidatos = busca.get("dados", [])
        if not candidatos:
            return f"Nenhum deputado encontrado com o nome '{nome}'."
        if len(candidatos) > 1:
            opcoes = "\n".join(f"- {c['nome']} ({c['siglaPartido']}/{c['siglaUf']}) — id {c['id']}" for c in candidatos)
            return f"Mais de um deputado encontrado para '{nome}'. Informe o id_deputado de um destes:\n{opcoes}"
        return candidatos[0]["id"]

    @staticmethod
    def _descrever_periodo(ano: int | None, mes: int | None) -> str:
        """Descreve o período das despesas em texto, para a mensagem de 'nenhum resultado'."""
        if ano and mes:
            return f" em {mes:02d}/{ano}"
        if ano:
            return f" em {ano}"
        return ""


# Instância única do cliente da Câmara, compartilhada pelas 3 tools deste módulo.
_cliente = ClienteCamara(http)


@mcp.tool(
    name="camara_buscar_deputados",
    annotations=ToolAnnotations(
        title="Busca de deputados federais",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def camara_buscar_deputados(nome: str | None = None, estado: str | None = None, partido: str | None = None, top: int = 10) -> str:
    """Consulta oficial da API de Dados Abertos da Câmara dos Deputados. Use esta
    tool sempre que a pergunta pedir para identificar, localizar ou listar
    deputados federais por nome, estado ou partido.

    Busca deputados federais em exercício por nome, estado (UF) e/ou partido.

    Args:
        nome: Nome ou trecho do nome do deputado (ex.: "Domingos Sávio").
        estado: Sigla da UF (ex.: "MG").
        partido: Sigla do partido (ex.: "PL").
        top: Quantidade máxima de resultados (padrão 10, máximo 50).
    """
    return await _cliente.buscar_deputados(nome, estado, partido, top)


@mcp.tool(
    name="camara_votacoes",
    annotations=ToolAnnotations(
        title="Votações de uma proposição na Câmara",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def camara_votacoes(
    sigla_tipo: str | None = None,
    numero: int | None = None,
    ano: int | None = None,
    id_votacao: str | None = None,
    top: int = 10,
) -> str:
    """Consulta oficial da API de Dados Abertos da Câmara dos Deputados. Use esta
    tool sempre que a pergunta envolver votação, aprovação/rejeição ou tramitação
    de um projeto de lei (PL), PEC, PLP ou outra proposição legislativa.

    Lista as votações de uma proposição legislativa (ex.: PL 1800/2023), ou os
    votos individuais de uma votação específica quando há registro nominal
    (nem toda votação da Câmara é nominal — votações simbólicas não têm votos
    individuais registrados, e a tool avisa isso em vez de inventar um resultado).

    Args:
        sigla_tipo: Tipo da proposição (ex.: "PL", "PEC", "PLP"). Use junto com
            `numero` e `ano` para localizar a proposição.
        numero: Número da proposição (ex.: 1800).
        ano: Ano de apresentação da proposição (ex.: 2023).
        id_votacao: Se você já sabe o id de uma votação específica (formato
            "idProposicao-sequencial", ex.: "2355754-35"), informe aqui para ver
            os votos individuais em vez da lista de votações da proposição.
        top: Quantidade máxima de votações a devolver (padrão 10, máximo 30).
    """
    return await _cliente.consultar_votacoes(sigla_tipo, numero, ano, id_votacao, top)


@mcp.tool(
    name="camara_despesas_deputado",
    annotations=ToolAnnotations(
        title="Despesas de um deputado (CEAP)",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def camara_despesas_deputado(id_deputado: int | None = None, nome: str | None = None, ano: int | None = None, mes: int | None = None, top: int = 20) -> str:
    """Consulta oficial do arquivo de despesas CEAP publicado pela Câmara dos
    Deputados. Use esta tool sempre que a pergunta envolver gasto, despesa,
    cota parlamentar ou transparência de um deputado — inclusive para o ano
    corrente, sem presumir ausência de dado.

    Despesas da Cota para Exercício da Atividade Parlamentar (CEAP) de um
    deputado — passagens, combustível, consultoria, divulgação etc.

    Args:
        id_deputado: Id numérico do deputado na Câmara. Se não souber, informe
            `nome` que eu localizo primeiro.
        nome: Nome do deputado, usado para localizar o id quando `id_deputado`
            não é informado. Se houver mais de um resultado, peço para você
            escolher pelo id.
        ano: Ano das despesas (ex.: 2026). Se omitido, usa o ano corrente.
        mes: Mês das despesas, de 1 a 12 (opcional).
        top: Quantidade máxima de despesas a devolver (padrão 20, máximo 100).
    """
    return await _cliente.despesas_deputado(id_deputado, nome, ano, mes, top)
