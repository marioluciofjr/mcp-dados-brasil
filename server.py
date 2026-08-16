"""Entrypoint do mcp-dados-brasil: importa cada módulo de tools/ (o que registra
suas tools na instância `mcp` compartilhada, definida em core.py) e expõe `app`,
a aplicação ASGI em Streamable HTTP que a Vercel detecta automaticamente.
"""

from __future__ import annotations

from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from core import mcp
from tools import camara, dou, ibge, noticias, pix, senado  # noqa: F401 — importados pelo efeito de registrar as tools

# Cria a aplicação ASGI em Streamable HTTP, no caminho /mcp, com CORS liberado
# para clientes remotos e modo stateless para rodar em hospedagem serverless
app = mcp.http_app(
    path="/mcp",
    stateless_http=True,
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["mcp-session-id"],
        )
    ],
)

if __name__ == "__main__":
    import os

    import uvicorn

    porta = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=porta)
