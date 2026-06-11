"""Testes do registro de feedback (server/feedback.py).

Não toca a rede: monkeypatcha settings (Supabase "configurado") e o httpx.AsyncClient.
Validação + caminho de insert + caminhos de erro.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from server import feedback


def _fake_settings(enabled: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        supabase_url="https://proj.supabase.co",
        supabase_anon_key="anon-key" if enabled else None,
        feedback_table="revcalc_feedback",
        feedback_enabled=enabled,
    )


class _FakeResp:
    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


class _FakeClient:
    """AsyncClient mock — captura o último POST e devolve uma resposta fixa."""

    last_call = {}

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, headers=None, json=None):
        _FakeClient.last_call = {"url": url, "headers": headers, "json": json}
        return _FakeClient._resp


# ── Validação ──

def test_tipo_invalido_rejeitado(monkeypatch):
    monkeypatch.setattr(feedback, "get_settings", lambda: _fake_settings())
    with pytest.raises(feedback.FeedbackError):
        import asyncio

        asyncio.run(feedback.registrar(tipo="xpto", mensagem="oi", email="a@b.com"))


def test_manual_sem_mensagem_rejeitado(monkeypatch):
    monkeypatch.setattr(feedback, "get_settings", lambda: _fake_settings())
    with pytest.raises(feedback.FeedbackError):
        import asyncio

        asyncio.run(feedback.registrar(tipo="bug", mensagem="   ", email="a@b.com", origem="manual"))


def test_indisponivel_sem_supabase(monkeypatch):
    monkeypatch.setattr(feedback, "get_settings", lambda: _fake_settings(enabled=False))
    with pytest.raises(feedback.FeedbackIndisponivel):
        import asyncio

        asyncio.run(feedback.registrar(tipo="feat", mensagem="ideia", email="a@b.com"))


# ── Insert (mockado) ──

def test_insert_ok_monta_row_e_headers(monkeypatch):
    import asyncio

    monkeypatch.setattr(feedback, "get_settings", lambda: _fake_settings())
    _FakeClient._resp = _FakeResp(201, "")  # return=minimal → corpo vazio
    monkeypatch.setattr(feedback.httpx, "AsyncClient", _FakeClient)

    out = asyncio.run(
        feedback.registrar(
            tipo="BUG",
            mensagem="cálculo errado",
            email="user@roseportaladvocacia.com.br",
            origem="manual",
            contexto={"url": "https://revcalc/x"},
        )
    )
    assert out["ok"] is True
    call = _FakeClient.last_call
    assert call["url"].endswith("/rest/v1/revcalc_feedback")
    assert call["headers"]["apikey"] == "anon-key"
    assert call["headers"]["Authorization"] == "Bearer anon-key"
    assert call["headers"]["Prefer"] == "return=minimal"
    assert call["json"]["tipo"] == "bug"  # normalizado
    assert call["json"]["email"] == "user@roseportaladvocacia.com.br"
    assert call["json"]["app_version"]  # versão anexada
    assert call["json"]["contexto"] == {"url": "https://revcalc/x"}


def test_auto_sem_mensagem_ok(monkeypatch):
    import asyncio

    monkeypatch.setattr(feedback, "get_settings", lambda: _fake_settings())
    _FakeClient._resp = _FakeResp(201, "")
    monkeypatch.setattr(feedback.httpx, "AsyncClient", _FakeClient)

    out = asyncio.run(
        feedback.registrar(
            tipo="erro_sistema", mensagem=None, email="a@b.com", origem="auto",
            contexto={"erro": "boom"},
        )
    )
    assert out["ok"] is True
    assert _FakeClient.last_call["json"]["origem"] == "auto"


def test_insert_http_erro_propaga(monkeypatch):
    import asyncio

    monkeypatch.setattr(feedback, "get_settings", lambda: _fake_settings())
    _FakeClient._resp = _FakeResp(500, {"message": "boom"})
    monkeypatch.setattr(feedback.httpx, "AsyncClient", _FakeClient)

    with pytest.raises(feedback.FeedbackError):
        asyncio.run(feedback.registrar(tipo="feat", mensagem="x", email="a@b.com"))
