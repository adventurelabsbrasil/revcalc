"""Testes do alerta de feedback pro Founder (server/notify.py). Não toca a rede."""

from __future__ import annotations

import pytest

from server import notify


def test_montar_texto_inclui_projeto_cliente_tipo_e_resumo():
    txt = notify.montar_texto_feedback(
        projeto="RevCalc",
        cliente="Rose Portal Advocacia",
        tipo="bug",
        origem="manual",
        email="bruna@roseportaladvocacia.com.br",
        mensagem="as linhas das parcelas não batem com o contrato",
        app_version="0.9.7",
    )
    assert "RevCalc" in txt and "Rose Portal Advocacia" in txt
    assert "Falha" in txt  # label do tipo bug
    assert "v0.9.7" in txt
    assert "bruna@roseportaladvocacia.com.br" in txt
    assert "linhas das parcelas" in txt


def test_montar_texto_marca_auto_e_trunca():
    txt = notify.montar_texto_feedback(
        projeto="RevCalc", cliente="Rose", tipo="erro_sistema", origem="auto",
        email=None, mensagem="x" * 500, app_version="0.9.7",
    )
    assert "(auto)" in txt
    assert "anônimo" in txt
    assert txt.rstrip().endswith("…")  # truncado


def test_normalizar_destino_grupo_e_numero():
    assert notify._normalizar_destino("12036304180@g.us") == "12036304180@g.us"
    assert notify._normalizar_destino("+55 (51) 99999-0000") == "5551999990000"


def test_enviar_whatsapp_noop_sem_config():
    import asyncio
    n = asyncio.run(notify.enviar_whatsapp(
        api_url=None, api_key=None, instance="adventure", destinos=(), text="oi"))
    assert n == 0


def test_enviar_whatsapp_posta_para_cada_destino(monkeypatch):
    import asyncio
    chamadas = []

    class _Resp:
        status_code = 201
        text = ""

    class _Client:
        def __init__(self, *a, **k):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False
        async def post(self, url, headers=None, json=None):
            chamadas.append({"url": url, "headers": headers, "json": json})
            return _Resp()

    monkeypatch.setattr(notify.httpx, "AsyncClient", _Client)
    n = asyncio.run(notify.enviar_whatsapp(
        api_url="https://wa.example.com", api_key="k", instance="adventure",
        destinos=("12036304180@g.us", "5551999990000"), text="alerta"))
    assert n == 2
    assert chamadas[0]["url"] == "https://wa.example.com/message/sendText/adventure"
    assert chamadas[0]["headers"]["apikey"] == "k"
    assert chamadas[0]["json"] == {"number": "12036304180@g.us", "text": "alerta"}
    assert chamadas[1]["json"]["number"] == "5551999990000"


def test_enviar_whatsapp_nao_lanca_em_erro(monkeypatch):
    import asyncio

    class _Boom:
        def __init__(self, *a, **k):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False
        async def post(self, *a, **k):
            raise RuntimeError("rede caiu")

    monkeypatch.setattr(notify.httpx, "AsyncClient", _Boom)
    n = asyncio.run(notify.enviar_whatsapp(
        api_url="https://wa.example.com", api_key="k", instance="adventure",
        destinos=("5551999990000",), text="x"))
    assert n == 0  # engoliu o erro, não lançou
