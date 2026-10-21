"""Testes do assistente administrativo (server/assistente.py + rotas /api/assistente).

Não toca a rede: um cliente Anthropic falso devolve uma sequência roteirizada de eventos
do stream da sessão e registra o que foi enviado.
"""

from __future__ import annotations

import json
from types import SimpleNamespace as NS

import pytest
from fastapi.testclient import TestClient

from server import app, assistente, auth_web


def _txt(texto):
    return NS(type="agent.message", content=[NS(type="text", text=texto)])


def _idle(motivo="end_turn"):
    return NS(type="session.status_idle", stop_reason=NS(type=motivo))


class _FakeStream:
    def __init__(self, eventos):
        self.eventos = eventos

    def __enter__(self):
        return iter(self.eventos)

    def __exit__(self, *exc):
        return False


class _FakeClient:
    def __init__(self, eventos):
        self.enviados = []
        events = NS(
            stream=lambda session_id: _FakeStream(eventos),
            send=lambda session_id, events: self.enviados.extend(events),
        )
        self.beta = NS(sessions=NS(events=events, create=lambda **kw: NS(id="sesn_nova")))


def test_conversar_junta_blocos_de_uma_mensagem():
    msg = NS(type="agent.message", content=[NS(type="text", text="a"), NS(type="thinking"), NS(type="text", text="b")])
    assert list(assistente.conversar(_FakeClient([msg, _idle()]), "s", "oi")) == ["ab"]


def test_conversar_rende_texto_e_para_no_idle():
    client = _FakeClient([_txt("Olá, "), _txt("achei 3 pastas."), _idle(), _txt("não chega")])
    assert list(assistente.conversar(client, "sesn_1", "oi")) == ["Olá, ", "achei 3 pastas."]
    assert client.enviados[0]["type"] == "user.message"
    assert client.enviados[0]["content"][0]["text"] == "oi"


def test_conversar_nega_ferramenta_por_padrao_e_segue_no_requires_action():
    pedido = NS(type="agent.tool_use", evaluated_permission="ask", id="sevt_9", name="write")
    client = _FakeClient([pedido, _idle("requires_action"), _txt("ok, não escrevi."), _idle()])
    assert list(assistente.conversar(client, "sesn_1", "salva isso")) == ["ok, não escrevi."]
    confirmacao = client.enviados[1]
    assert confirmacao["type"] == "user.tool_confirmation"
    assert confirmacao["tool_use_id"] == "sevt_9"
    assert confirmacao["result"] == "deny"


def test_conversar_ignora_erro_em_retentativa_e_falha_no_terminal():
    erro = lambda status: NS(  # noqa: E731
        type="session.error",
        error=NS(type="model_overloaded_error", message="ocupado", retry_status=NS(type=status)),
    )
    client = _FakeClient([erro("retrying"), _txt("voltei"), _idle()])
    assert list(assistente.conversar(client, "s", "oi")) == ["voltei"]

    client = _FakeClient([erro("terminal")])
    with pytest.raises(assistente.AssistenteErro, match="model_overloaded_error"):
        list(assistente.conversar(client, "s", "oi"))


@pytest.mark.parametrize("motivo", ["retries_exhausted", "budget_reached"])
def test_conversar_falha_em_idle_sem_resposta(motivo):
    with pytest.raises(assistente.AssistenteErro):
        list(assistente.conversar(_FakeClient([_idle(motivo)]), "s", "oi"))


def test_token_de_conversa_amarra_ao_email():
    token = auth_web.assinar_conversa("sesn_1", "a@x.com")
    assert auth_web.ler_conversa(token, "a@x.com") == "sesn_1"
    assert auth_web.ler_conversa(token, "b@x.com") is None
    assert auth_web.ler_conversa("lixo", "a@x.com") is None


# ─── Rotas ──────────────────────────────────────────────────────────────────

def _eventos_sse(resp):
    return [json.loads(l[len("data: "):]) for l in resp.text.splitlines() if l.startswith("data: ")]


@pytest.fixture
def logado(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-teste")
    for nome in assistente.CONFIG:
        monkeypatch.setenv(nome, f"{nome.lower()}_teste")
    client = TestClient(app.app)
    client.cookies.set(app.get_settings().cookie_name, auth_web.assinar_sessao("a@x.com"))
    return client


def test_mensagem_exige_login():
    assert TestClient(app.app).post("/api/assistente/mensagem", json={"texto": "oi"}).status_code == 401


def test_mensagem_indisponivel_sem_chave(logado, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    assert logado.get("/api/assistente/config").json() == {"enabled": False}
    assert logado.post("/api/assistente/mensagem", json={"texto": "oi"}).status_code == 503


def test_indisponivel_sem_vault(logado, monkeypatch):
    monkeypatch.delenv("ASSISTENTE_VAULT_ID")
    assert logado.get("/api/assistente/config").json() == {"enabled": False}


def test_mensagem_nova_conversa_devolve_token_e_texto(logado, monkeypatch):
    fake = _FakeClient([_txt("Achei a pasta."), _idle()])
    monkeypatch.setattr(assistente, "criar_cliente", lambda: fake)
    resp = logado.post("/api/assistente/mensagem", json={"texto": "pasta da Maria?"})
    assert resp.status_code == 200
    evs = _eventos_sse(resp)
    assert evs[0]["tipo"] == "conversa"
    assert auth_web.ler_conversa(evs[0]["token"], "a@x.com") == "sesn_nova"
    assert evs[1:] == [{"tipo": "texto", "texto": "Achei a pasta."}, {"tipo": "fim"}]


def test_mensagem_reusa_conversa_do_token(logado, monkeypatch):
    fake = _FakeClient([_txt("de novo"), _idle()])
    fake.beta.sessions.create = lambda **kw: pytest.fail("não devia criar sessão")
    monkeypatch.setattr(assistente, "criar_cliente", lambda: fake)
    token = auth_web.assinar_conversa("sesn_1", "a@x.com")
    evs = _eventos_sse(logado.post("/api/assistente/mensagem", json={"texto": "e aí?", "conversa": token}))
    assert evs == [{"tipo": "texto", "texto": "de novo"}, {"tipo": "fim"}]


def test_mensagem_erro_do_agente_vira_evento(logado, monkeypatch):
    fake = _FakeClient([NS(type="session.status_terminated")])
    monkeypatch.setattr(assistente, "criar_cliente", lambda: fake)
    evs = _eventos_sse(logado.post("/api/assistente/mensagem", json={"texto": "oi"}))
    assert evs[-1]["tipo"] == "erro" and evs[-1]["reiniciar"] is True
