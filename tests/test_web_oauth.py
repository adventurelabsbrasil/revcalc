from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from calculadora_crefaz.exceptions import AuthError
from server import app, auth_web, token_store


def test_authorization_generates_s256():
    from urllib.parse import parse_qs, urlparse
    url, state, verifier = auth_web.authorization_url()
    query = parse_qs(urlparse(url).query)
    assert state and verifier
    assert query["code_challenge_method"] == ["S256"]


@pytest.mark.parametrize("cookie_case", ["missing_state", "wrong_state", "missing_verifier", "invalid_verifier"])
def test_callback_rejects_incomplete_transaction(monkeypatch, cookie_case):
    client = TestClient(app.app)
    called = []
    monkeypatch.setattr(auth_web, "trocar_code", lambda *a, **k: called.append(k))
    if cookie_case != "missing_state":
        client.cookies.set(app.STATE_COOKIE, auth_web.assinar_state("other" if cookie_case == "wrong_state" else "valid-state"))
    if cookie_case not in ("missing_verifier",):
        client.cookies.set(app.VERIFIER_COOKIE, "invalid" if cookie_case == "invalid_verifier" else auth_web.assinar_verifier("verifier"))
    response = client.get("/api/auth/callback?code=fake&state=valid-state", follow_redirects=False)
    assert response.status_code == 302
    assert "state_invalido" in response.headers["location"]
    assert not called


def test_valid_callback_keeps_server_token_storage(monkeypatch):
    client = TestClient(app.app)
    client.cookies.set(app.STATE_COOKIE, auth_web.assinar_state("state"))
    client.cookies.set(app.VERIFIER_COOKIE, auth_web.assinar_verifier("verifier"))
    c = object()
    calls = []
    def exchange(code, state=None, code_verifier=None):
        assert (code, state, code_verifier) == ("fake", "state", "verifier")
        return "user@adventurelabs.com.br", c
    monkeypatch.setattr(auth_web, "trocar_code", exchange)
    monkeypatch.setattr(token_store, "save", lambda e, creds: calls.append((e, creds)))
    response = client.get("/api/auth/callback?code=fake&state=state", follow_redirects=False)
    assert calls == [("user@adventurelabs.com.br", c)]
    assert "logado=1" in response.headers["location"]
    assert "HttpOnly" in str(response.headers.get_list("set-cookie"))


def test_code_exchange_requires_verifier():
    with pytest.raises(AuthError):
        auth_web.trocar_code("fake", state="valid", code_verifier=None)


def test_web_restored_account_rechecks_policy(monkeypatch):
    calls = []
    monkeypatch.setattr(token_store, "load", lambda e: calls.append(e))
    assert token_store.carregar_sessao("user@gmail.com") is None
    assert not calls
