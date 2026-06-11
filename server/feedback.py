"""Feedback do app → Supabase (public.revcalc_feedback).

Insere via PostgREST com a ANON key (não a service_role) — least-privilege: a anon
só consegue INSERT (policy revcalc_feedback_insert_anon), não lê nem toca outra
tabela. A service_role NÃO vive aqui de propósito (bypassaria o RLS do banco
inteiro num container client-facing). Usa Prefer: return=minimal porque a anon não
tem SELECT/RETURNING na tabela.

Degrada gracioso: se o Supabase não estiver configurado, `enabled()` é False e o
endpoint responde 503 sem derrubar o resto do app.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from calculadora_crefaz import __version__ as APP_VERSION
from .settings import get_settings

logger = logging.getLogger(__name__)

TIPOS_VALIDOS = {"feat", "bug", "erro_sistema", "duvida"}
ORIGENS_VALIDAS = {"manual", "auto"}

# Limites defensivos (anti-abuso / payload sadio).
MAX_MENSAGEM = 4000
MAX_CONTEXTO_BYTES = 16_000


class FeedbackError(Exception):
    """Erro de validação ou de gravação do feedback."""


class FeedbackIndisponivel(FeedbackError):
    """Supabase não configurado — feature desligada."""


def enabled() -> bool:
    return get_settings().feedback_enabled


def _validar_tipo(tipo: Any) -> str:
    t = (tipo or "").strip().lower()
    if t not in TIPOS_VALIDOS:
        raise FeedbackError(f"tipo inválido: {tipo!r} (esperado um de {sorted(TIPOS_VALIDOS)})")
    return t


def _validar_origem(origem: Any) -> str:
    o = (origem or "manual").strip().lower()
    if o not in ORIGENS_VALIDAS:
        raise FeedbackError(f"origem inválida: {origem!r}")
    return o


async def registrar(
    *,
    tipo: Any,
    mensagem: Optional[str],
    email: Optional[str],
    origem: Any = "manual",
    contexto: Optional[dict] = None,
    severidade: Optional[str] = None,
) -> dict:
    """Valida e insere uma linha de feedback. Retorna a linha criada (id, created_at...)."""
    s = get_settings()
    if not s.feedback_enabled:
        raise FeedbackIndisponivel(
            "Feedback indisponível: SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY não configurados."
        )

    tipo = _validar_tipo(tipo)
    origem = _validar_origem(origem)

    msg = (mensagem or "").strip()
    if origem == "manual" and not msg:
        raise FeedbackError("Escreva uma mensagem antes de enviar.")
    if len(msg) > MAX_MENSAGEM:
        msg = msg[:MAX_MENSAGEM]

    ctx = contexto if isinstance(contexto, dict) else {}
    # Trunca contexto absurdo (proteção; não confia no cliente).
    import json

    if len(json.dumps(ctx, ensure_ascii=False)) > MAX_CONTEXTO_BYTES:
        ctx = {"_truncado": True, "nota": "contexto excedeu o limite e foi descartado"}

    row = {
        "tipo": tipo,
        "mensagem": msg or None,
        "email": (email or None),
        "origem": origem,
        "contexto": ctx,
        "app_version": APP_VERSION,
    }
    if severidade:
        row["severidade"] = severidade

    url = f"{s.supabase_url}/rest/v1/{s.feedback_table}"
    headers = {
        "apikey": s.supabase_anon_key,
        "Authorization": f"Bearer {s.supabase_anon_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",  # anon não tem SELECT/RETURNING na tabela
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, headers=headers, json=row)

    # return=minimal → 201 com corpo vazio no sucesso.
    if resp.status_code not in (200, 201, 204):
        logger.error("Feedback insert falhou: %s %s", resp.status_code, resp.text[:500])
        raise FeedbackError(f"Falha ao gravar o feedback (HTTP {resp.status_code}).")

    return {"ok": True}
