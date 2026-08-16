"""Tools do Senado Federal: busca de senadores em exercício e matérias
legislativas de autoria de um senador, direto na API de Dados Abertos do Senado.

Fonte: https://legis.senado.leg.br/dadosabertos — pública, sem chave.

Como está organizado: a classe ClienteSenado concentra toda a lógica de acesso
à API do Senado. As funções com @mcp.tool são só a porta de entrada do FastMCP,
cada uma delegando para o método correspondente da classe.
"""

from __future__ import annotations

import unicodedata

from mcp.types import ToolAnnotations

from core import ClienteHTTP, ErroConsultaExterna, http, mcp


class ClienteSenado:
    """Encapsula toda a integração com a API de Dados Abertos do Senado Federal."""

    _BASE_URL = "https://legis.senado.leg.br/dadosabertos"
    _CABECALHOS = {"Accept": "application/json"}

    def __init__(self, cliente_http: ClienteHTTP) -> None:
        self._http = cliente_http

    async def buscar_senadores(self, nome: str | None, estado: str | None, partido: str | None, top: int) -> str:
        """Busca, na lista de senadores em exercício, quem bate com os filtros informados."""
        top = max(1, min(top, 81))

        try:
            senadores = await self._listar_em_exercicio()
        except ErroConsultaExterna as exc:
            return f"Não consegui consultar a lista de senadores: {exc}"

        termo = self._normalizar(nome) if nome else None
        sigla_estado = estado.strip().upper() if estado else None
        termo_partido = self._normalizar(partido) if partido else None

        encontrados = []
        for s in senadores:
            ident = s["IdentificacaoParlamentar"]
            if termo and termo not in self._normalizar(ident["NomeParlamentar"]):
                continue
            if sigla_estado and ident["UfParlamentar"] != sigla_estado:
                continue
            if termo_partido and termo_partido not in self._normalizar(ident["SiglaPartidoParlamentar"]):
                continue
            encontrados.append(ident)
            if len(encontrados) >= top:
                break

        if not encontrados:
            return "Nenhum senador encontrado para os filtros informados."

        linhas = [f"Senadores encontrados — {len(encontrados)} resultado(s):\n"]
        for s in encontrados:
            linhas.append(f"- {s['NomeParlamentar']} ({s['SiglaPartidoParlamentar']}/{s['UfParlamentar']}) — código {s['CodigoParlamentar']}, e-mail {s.get('EmailParlamentar') or 'não informado'}")
        linhas.append("\nFonte: Senado Federal — API de Dados Abertos.")
        return "\n".join(linhas)

    async def materias_de_autoria(self, codigo_senador: int | None, nome: str | None, top: int) -> str:
        """Resolve o código do senador (por nome, se preciso) e lista as matérias de autoria dele."""
        top = max(1, min(top, 50))

        if not codigo_senador:
            if not nome:
                return "Informe 'codigo_senador' ou 'nome' do senador para eu consultar as matérias."
            codigo_ou_erro = await self._resolver_codigo_por_nome(nome)
            if isinstance(codigo_ou_erro, str):
                return codigo_ou_erro  # já é a mensagem de erro/ambiguidade pronta
            codigo_senador = codigo_ou_erro

        try:
            dados = await self._http.buscar_json(f"{self._BASE_URL}/senador/{codigo_senador}/autorias", headers=self._CABECALHOS)
        except ErroConsultaExterna as exc:
            return f"Não consegui consultar as matérias do senador código {codigo_senador}: {exc}"

        parlamentar = dados.get("MateriasAutoriaParlamentar", {}).get("Parlamentar", {})
        autorias = parlamentar.get("Autorias", {}).get("Autoria", [])
        if isinstance(autorias, dict):  # a API devolve um dict solto (não lista) quando há só 1 resultado
            autorias = [autorias]
        if not autorias:
            return f"Nenhuma matéria de autoria encontrada para o senador código {codigo_senador}."

        autorias = autorias[:top]
        linhas = [f"Matérias de autoria de {parlamentar.get('Nome', codigo_senador)} — {len(autorias)} resultado(s):\n"]
        for a in autorias:
            m = a["Materia"]
            principal = "autor principal" if a.get("IndicadorAutorPrincipal") == "Sim" else "coautor"
            linhas.append(f"- {m.get('DescricaoIdentificacao', '?')} ({m.get('Data', '?')}, {principal}): {m.get('Ementa', 'sem ementa registrada')}")
        linhas.append(
            "\nFonte: Senado Federal — API de Dados Abertos. Nota: este endpoint está em "
            "processo de descontinuação pelo Senado, em favor de um novo serviço unificado "
            "(https://legis.senado.leg.br/dadosabertos/processo); ainda funciona no momento, "
            "mas pode ser desativado no futuro."
        )
        return "\n".join(linhas)

    async def _resolver_codigo_por_nome(self, nome: str) -> int | str:
        """Busca o senador pelo nome. Devolve o código se achar só 1 resultado, ou
        uma mensagem pronta (erro ou lista de opções) se achar 0 ou mais de 1."""
        try:
            senadores = await self._listar_em_exercicio()
        except ErroConsultaExterna as exc:
            return f"Não consegui localizar o senador '{nome}': {exc}"
        termo = self._normalizar(nome)
        candidatos = [s["IdentificacaoParlamentar"] for s in senadores if termo in self._normalizar(s["IdentificacaoParlamentar"]["NomeParlamentar"])]
        if not candidatos:
            return f"Nenhum senador encontrado com o nome '{nome}'."
        if len(candidatos) > 1:
            opcoes = "\n".join(f"- {c['NomeParlamentar']} ({c['SiglaPartidoParlamentar']}/{c['UfParlamentar']}) — código {c['CodigoParlamentar']}" for c in candidatos)
            return f"Mais de um senador encontrado para '{nome}'. Informe o codigo_senador de um destes:\n{opcoes}"
        return int(candidatos[0]["CodigoParlamentar"])

    async def _listar_em_exercicio(self) -> list[dict]:
        """Busca a lista completa de senadores em exercício (~81 registros — sem
        necessidade de cache, a resposta já é pequena e rápida)."""
        dados = await self._http.buscar_json(f"{self._BASE_URL}/senador/lista/atual", headers=self._CABECALHOS)
        return dados["ListaParlamentarEmExercicio"]["Parlamentares"]["Parlamentar"]

    @staticmethod
    def _normalizar(texto: str) -> str:
        """Remove acentos e baixa a caixa, para comparar nomes com tolerância a acentuação."""
        sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
        return sem_acento.lower()


# Instância única do cliente do Senado, compartilhada pelas 2 tools deste módulo.
_cliente = ClienteSenado(http)


@mcp.tool(
    name="senado_buscar_senadores",
    annotations=ToolAnnotations(
        title="Busca de senadores em exercício",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def senado_buscar_senadores(nome: str | None = None, estado: str | None = None, partido: str | None = None, top: int = 10) -> str:
    """Busca senadores em exercício por nome, estado (UF) e/ou partido.

    Args:
        nome: Nome ou trecho do nome do senador (ex.: "Alan Rick").
        estado: Sigla da UF (ex.: "AC").
        partido: Sigla do partido (ex.: "REPUBLICANOS").
        top: Quantidade máxima de resultados (padrão 10, máximo 81 — o total de senadores).
    """
    return await _cliente.buscar_senadores(nome, estado, partido, top)


@mcp.tool(
    name="senado_materias",
    annotations=ToolAnnotations(
        title="Matérias legislativas de um senador",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def senado_materias(codigo_senador: int | None = None, nome: str | None = None, top: int = 15) -> str:
    """Lista as matérias legislativas (projetos de lei, requerimentos etc.) de
    autoria de um senador.

    Args:
        codigo_senador: Código numérico do senador no Senado. Se não souber,
            informe `nome` que eu localizo primeiro.
        nome: Nome do senador, usado para localizar o código quando
            `codigo_senador` não é informado. Se houver mais de um resultado,
            peço para você escolher pelo código.
        top: Quantidade máxima de matérias a devolver (padrão 15, máximo 50).
    """
    return await _cliente.materias_de_autoria(codigo_senador, nome, top)
