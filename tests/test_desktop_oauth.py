"""Protocol tests use real oauthlib/credentials and fake Google/keyring only."""

import base64
import hashlib
import json
import threading
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen

import pytest
import requests
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from keyring.backends.Windows import WinVaultKeyring

from calculadora_crefaz import auth
from calculadora_crefaz.config import OAUTH_SCOPES
from calculadora_crefaz.exceptions import AuthError

EMAIL = "user@adventurelabs.com.br"
CID = "123-test.apps.googleusercontent.com"


@pytest.fixture
def vault(monkeypatch):
    saved = {}
    monkeypatch.setattr(auth.keyring, "get_keyring", lambda: WinVaultKeyring())
    monkeypatch.setattr(auth.keyring, "set_password", lambda s, k, v: saved.__setitem__((s, k), v))
    monkeypatch.setattr(auth.keyring, "get_password", lambda s, k: saved.get((s, k)))
    monkeypatch.setattr(auth.keyring, "delete_password", lambda s, k: saved.pop((s, k), None))
    monkeypatch.setattr(auth, "_email_do_token", lambda c: EMAIL)
    monkeypatch.setattr(auth, "load_profile", lambda: {})
    monkeypatch.setenv("GOOGLE_OAUTH_DESKTOP_CLIENT_ID", CID)
    return saved


def creds(secret="", expired=False, scopes=None):
    return Credentials(
        "fake-access", refresh_token="fake-refresh", client_id=CID,
        client_secret=secret, token_uri="https://oauth2.googleapis.com/token",
        scopes=OAUTH_SCOPES if scopes is None else scopes,
        expiry=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=-1 if expired else 1),
    )


@pytest.mark.parametrize("secret", ["", "legacy-desktop-secret"])
def test_keyring_roundtrip_and_real_refresh(vault, monkeypatch, secret):
    c = creds(secret=secret, expired=True)
    auth._salvar_token(EMAIL, c)
    calls = []

    def google_request(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(status=200, data=json.dumps({
            "access_token": "new-access", "expires_in": 3600,
            "token_type": "Bearer", "scope": " ".join(OAUTH_SCOPES),
        }).encode())

    monkeypatch.setattr(auth, "Request", lambda: google_request)
    session = auth.carregar_sessao_existente()
    assert session.email == EMAIL
    assert session.credentials.token == "new-access"
    body = parse_qs(calls[0]["body"].decode(), keep_blank_values=True)
    assert body["client_id"] == [CID]
    assert body.get("client_secret", [""]) == [secret]
    assert calls[0]["url"] == "https://oauth2.googleapis.com/token"
    assert json.loads(vault[(auth.KEYRING_SERVICE, auth._username_para_email(EMAIL))])["token"] == "new-access"


def test_public_token_without_secret_field_restores(vault):
    data = json.loads(creds().to_json())
    data.pop("client_secret")
    vault[(auth.KEYRING_SERVICE, "ultimo-email")] = EMAIL
    vault[(auth.KEYRING_SERVICE, auth._username_para_email(EMAIL))] = json.dumps(data)
    assert auth.carregar_sessao_existente().credentials.client_secret == ""


@pytest.mark.parametrize("payload", ["broken", "[]", "{}", "null"])
def test_corrupt_token_requests_new_login(vault, payload):
    vault[(auth.KEYRING_SERVICE, "ultimo-email")] = EMAIL
    vault[(auth.KEYRING_SERVICE, auth._username_para_email(EMAIL))] = payload
    assert auth.carregar_sessao_existente() is None


def test_restored_session_rechecks_domain_and_identity(vault, monkeypatch):
    auth._salvar_token(EMAIL, creds())
    monkeypatch.setattr(auth, "_email_do_token", lambda c: "other@adventurelabs.com.br")
    assert auth.carregar_sessao_existente() is None
    monkeypatch.setattr(auth, "_validar_dominio", lambda e: (_ for _ in ()).throw(AuthError("removed")))
    assert auth.carregar_sessao_existente() is None
    assert vault  # no deletion during migration/denial


def test_revoked_refresh_does_not_log_credentials(vault, monkeypatch, caplog):
    auth._salvar_token(EMAIL, creds(expired=True))
    def fail(**kwargs):
        raise RefreshError("fake-refresh secret-response")
    monkeypatch.setattr(auth, "Request", lambda: fail)
    assert auth.carregar_sessao_existente() is None
    assert "fake-refresh" not in caplog.text


@pytest.mark.parametrize("failure", [AuthError("denied"), RuntimeError("code=secret")])
def test_failed_login_never_persists(vault, monkeypatch, failure):
    monkeypatch.setattr(InstalledAppFlow, "run_local_server", lambda *a, **k: (_ for _ in ()).throw(failure))
    with pytest.raises(AuthError) as error:
        auth.fluxo_login()
    assert "secret" not in str(error.value)
    assert not vault


def test_missing_granted_scope_never_persists(vault, monkeypatch):
    c = creds()
    c._granted_scopes = []
    monkeypatch.setattr(InstalledAppFlow, "run_local_server", lambda *a, **k: c)
    with pytest.raises(AuthError, match="permissões"):
        auth.fluxo_login()
    assert not vault


def test_disallowed_account_never_persists(vault, monkeypatch):
    monkeypatch.setattr(InstalledAppFlow, "run_local_server", lambda *a, **k: creds())
    monkeypatch.setattr(auth, "_email_do_token", lambda c: "user@gmail.com")
    with pytest.raises(AuthError):
        auth.fluxo_login()
    assert not vault


def test_missing_offline_grant_never_persists(vault, monkeypatch):
    c = creds()
    c._refresh_token = None
    monkeypatch.setattr(InstalledAppFlow, "run_local_server", lambda *a, **k: c)
    with pytest.raises(AuthError, match="persistente"):
        auth.fluxo_login()
    assert not vault


def test_insecure_keyring_rejected(monkeypatch):
    monkeypatch.setattr(auth.sys, "platform", "win32")
    monkeypatch.setattr(auth.keyring, "get_keyring", lambda: object())
    with pytest.raises(AuthError, match="Credential Manager"):
        auth.ultimo_email_logado()


def test_logout_uses_existing_keyring_names(vault):
    auth._salvar_token(EMAIL, creds())
    auth.logout()
    assert not vault


@pytest.mark.parametrize("bad_state", [False, True])
def test_real_loopback_pkce_and_state(vault, monkeypatch, bad_state):
    """Browser redirects to a real ephemeral socket; token HTTP is intercepted."""
    from requests_oauthlib import OAuth2Session
    observed = {}
    threads = []

    def browser_open(url, **kwargs):
        query = parse_qs(urlparse(url).query)
        observed["authorization"] = query
        redirect = query["redirect_uri"][0]
        assert urlparse(redirect).hostname == "127.0.0.1"
        assert urlparse(redirect).port > 0
        state = "wrong-state" if bad_state else query["state"][0]
        def callback():
            with urlopen(redirect + "?code=fake-code&state=" + state, timeout=5) as response:
                response.read()
        thread = threading.Thread(target=callback)
        threads.append(thread)
        thread.start()
        return True

    def token_request(self, method, url, **kwargs):
        assert url == "https://oauth2.googleapis.com/token"
        observed["token"] = kwargs["data"]
        response = requests.Response()
        response.status_code = 200
        response.request = requests.Request(method, url, data=kwargs["data"]).prepare()
        response._content = json.dumps({
            "access_token": "fake-access", "refresh_token": "fake-refresh",
            "expires_in": 3600, "token_type": "Bearer", "scope": " ".join(OAUTH_SCOPES),
        }).encode()
        return response

    monkeypatch.setattr("google_auth_oauthlib.flow.webbrowser.get", lambda b: SimpleNamespace(open=browser_open))
    monkeypatch.setattr(OAuth2Session, "request", token_request)
    if bad_state:
        with pytest.raises(AuthError):
            auth.fluxo_login()
        assert "token" not in observed
        assert not vault
    else:
        assert auth.fluxo_login().email == EMAIL
        query = observed["authorization"]
        body = observed["token"]
        verifier = body["code_verifier"]
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        assert query["code_challenge"] == [challenge]
        assert query["code_challenge_method"] == ["S256"]
        assert body["code"] == "fake-code"
        assert body["client_id"] == CID
        assert body.get("client_secret", "") == ""
    for thread in threads:
        thread.join(timeout=5)
        assert not thread.is_alive()


def test_loopback_timeout_closes_socket():
    from google_auth_oauthlib.flow import WSGITimeoutError
    flow = InstalledAppFlow.from_client_config(auth._client_config(CID), OAUTH_SCOPES, autogenerate_code_verifier=True)
    with pytest.raises(WSGITimeoutError):
        flow.run_local_server(host="127.0.0.1", port=0, open_browser=False, authorization_prompt_message=None, timeout_seconds=0.01)
    import socket
    port = urlparse(flow.redirect_uri).port
    with socket.socket() as connection:
        assert connection.connect_ex(("127.0.0.1", port)) != 0
