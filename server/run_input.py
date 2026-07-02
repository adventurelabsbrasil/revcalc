"""Helpers puros do endpoint /api/run — sem dependências web, testáveis isolados.

Separado de `server.app` (que importa FastAPI) para os testes rodarem sem instalar
o stack web (o backend roda em container no xeon com deps próprias)."""

from __future__ import annotations


def extrair_nomes(body: dict) -> list[str]:
    """Nomes válidos (≥2 palavras) do corpo do /api/run (v0.9.8).

    Aceita `{"nomes": [...]}` (lote) ou `{"nome": "..."}` (compat single). Descarta
    entradas não-string, vazias ou com <2 palavras; normaliza espaços. Lista vazia
    = nada válido → o endpoint responde 400."""
    nomes_raw = body.get("nomes")
    if nomes_raw is None:
        um = body.get("nome")
        nomes_raw = [um] if um else []
    if not isinstance(nomes_raw, list):
        return []
    return [
        " ".join(n.split())
        for n in nomes_raw
        if isinstance(n, str) and len(n.split()) >= 2
    ]
