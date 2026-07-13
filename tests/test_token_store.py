"""Testes do token store dual-backend (server/token_store.py).

Não toca a rede nem o Google: monkeypatcha settings + httpx.Client. Cobre o
dispatch disk/supabase, a montagem do PostgREST (URL/headers/payload) e que o
ciphertext gravado é recuperável (Fernet round-trip).
"""

from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet

from server import token_store


# ── fixtures/helpers ──

_ENC_KEY = Fernet.generate_key().decode()  # chave Fernet fixa p/ os testes


def _settings(*, supabase: bool, tmp_path=None) -> SimpleNamespace:
    return SimpleNamespace(
        supabase_url="https://proj.supabase.co",
        supabase_anon_key="anon-key",
        oauth_table="revcalc_oauth_tokens",
        token_store_supabase=supabase,
        token_enc_key=_ENC_KEY,
        session_secret="test-secret",
        token_store_path=tmp_path,
    )


class _FakeResp:
    def __init__(self, status_code, payload=""):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


class _FakeClient:
    """httpx.Client mock (sync) — captura a última chamada e devolve resposta fixa."""

    last = {}
    resp = _FakeResp(200, [])

    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get(self, url, headers=None, params=None):
        _FakeClient.last = {"method": "GET", "url": url, "headers": headers, "params": params}
        return _FakeClient.resp

    def post(self, url, headers=None, json=None):
        _FakeClient.last = {"method": "POST", "url": url, "headers": headers, "json": json}
        return _FakeClient.resp

    def delete(self, url, headers=None, params=None):
        _FakeClient.last = {"method": "DELETE", "url": url, "headers": headers, "params": params}
        return _FakeClient.resp


class _FakeCreds:
    def __init__(self, payload: dict):
        self._payload = payload

    def to_json(self) -> str:
        return json.dumps(self._payload)


def _hash(email: str) -> str:
    return hashlib.sha256(email.lower().encode()).hexdigest()


# ── email hash ──

def test_email_hash_estavel():
    assert token_store._email_hash("A@B.com") == _hash("a@b.com")


# ── save (supabase) ──

def test_save_supabase_faz_upsert(monkeypatch):
    monkeypatch.setattr(token_store, "get_settings", lambda: _settings(supabase=True))
    _FakeClient.resp = _FakeResp(201, "")
    monkeypatch.setattr(token_store.httpx, "Client", _FakeClient)

    token_store.save("user@x.com", _FakeCreds({"refresh_token": "z"}))

    call = _FakeClient.last
    assert call["method"] == "POST"
    assert call["url"].endswith("/rest/v1/revcalc_oauth_tokens")
    assert call["headers"]["apikey"] == "anon-key"
    assert call["headers"]["Authorization"] == "Bearer anon-key"
    assert "merge-duplicates" in call["headers"]["Prefer"]
    assert call["json"]["email_hash"] == _hash("user@x.com")
    assert call["json"]["encrypted_creds"]  # ciphertext não-vazio


def test_save_supabase_ciphertext_recuperavel(monkeypatch):
    """O que sobe é exatamente Fernet(creds.to_json()) — decripta de volta igual."""
    monkeypatch.setattr(token_store, "get_settings", lambda: _settings(supabase=True))
    _FakeClient.resp = _FakeResp(201, "")
    monkeypatch.setattr(token_store.httpx, "Client", _FakeClient)

    payload = {"refresh_token": "z", "client_id": "cid"}
    token_store.save("user@x.com", _FakeCreds(payload))

    ciphertext = _FakeClient.last["json"]["encrypted_creds"].encode()
    recuperado = Fernet(_ENC_KEY.encode()).decrypt(ciphertext)
    assert json.loads(recuperado) == payload


def test_save_supabase_erro_levanta(monkeypatch):
    monkeypatch.setattr(token_store, "get_settings", lambda: _settings(supabase=True))
    _FakeClient.resp = _FakeResp(500, {"message": "boom"})
    monkeypatch.setattr(token_store.httpx, "Client", _FakeClient)

    with pytest.raises(RuntimeError):
        token_store.save("user@x.com", _FakeCreds({"refresh_token": "z"}))


# ── load (supabase) ──

def test_load_supabase_ausente_retorna_none(monkeypatch):
    monkeypatch.setattr(token_store, "get_settings", lambda: _settings(supabase=True))
    _FakeClient.resp = _FakeResp(200, [])  # nenhuma linha
    monkeypatch.setattr(token_store.httpx, "Client", _FakeClient)

    assert token_store.load("nobody@x.com") is None
    assert _FakeClient.last["method"] == "GET"
    assert _FakeClient.last["params"]["email_hash"] == f"eq.{_hash('nobody@x.com')}"


def test_load_supabase_falha_rede_retorna_none(monkeypatch):
    """Blip do Supabase degrada p/ re-auth (None), não 500."""
    monkeypatch.setattr(token_store, "get_settings", lambda: _settings(supabase=True))

    class _Boom(_FakeClient):
        def get(self, *a, **k):
            raise RuntimeError("network down")

    monkeypatch.setattr(token_store.httpx, "Client", _Boom)
    assert token_store.load("user@x.com") is None


def test_load_supabase_decripta_e_reconstroi(monkeypatch):
    """Row com ciphertext válido → decripta → Credentials (mockado) válido é retornado."""
    monkeypatch.setattr(token_store, "get_settings", lambda: _settings(supabase=True))
    blob = Fernet(_ENC_KEY.encode()).encrypt(json.dumps({"refresh_token": "z"}).encode())
    _FakeClient.resp = _FakeResp(200, [{"encrypted_creds": blob.decode()}])
    monkeypatch.setattr(token_store.httpx, "Client", _FakeClient)

    fake_creds = SimpleNamespace(expired=False, valid=True, refresh_token="z")
    monkeypatch.setattr(
        token_store.Credentials, "from_authorized_user_info",
        classmethod(lambda cls, info, scopes: fake_creds),
    )
    assert token_store.load("user@x.com") is fake_creds


# ── delete (supabase) ──

def test_delete_supabase(monkeypatch):
    monkeypatch.setattr(token_store, "get_settings", lambda: _settings(supabase=True))
    _FakeClient.resp = _FakeResp(204, "")
    monkeypatch.setattr(token_store.httpx, "Client", _FakeClient)

    token_store.delete("user@x.com")
    assert _FakeClient.last["method"] == "DELETE"
    assert _FakeClient.last["params"]["email_hash"] == f"eq.{_hash('user@x.com')}"


# ── dispatch p/ disco ──

def test_save_disco_grava_arquivo(monkeypatch, tmp_path):
    monkeypatch.setattr(
        token_store, "get_settings", lambda: _settings(supabase=False, tmp_path=tmp_path)
    )
    token_store.save("user@x.com", _FakeCreds({"refresh_token": "z"}))

    arquivo = tmp_path / f"{_hash('user@x.com')}.enc"
    assert arquivo.exists()
    # ciphertext recuperável
    assert json.loads(Fernet(_ENC_KEY.encode()).decrypt(arquivo.read_bytes())) == {"refresh_token": "z"}
