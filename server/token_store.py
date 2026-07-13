"""Token store server-side, cifrado. Dois backends, MESMA API pública.

Um token por email (chave = `sha256(email)`), conteúdo = `Fernet(creds.to_json())`.
A chave Fernet vem de TOKEN_ENC_KEY ou é derivada do SESSION_SECRET. O token NUNCA
vai para o browser — o front só carrega um cookie de sessão opaco.

Backends (env `TOKEN_STORE_BACKEND`):
  - `disk` (default): um arquivo `<sha256(email)>.enc` no volume (`TOKEN_STORE_PATH`).
  - `supabase`: uma linha em `public.revcalc_oauth_tokens` (via PostgREST + ANON key,
    server-side). Estado COMPARTILHADO entre hosts → habilita HA ativo/ativo sem que a
    sessão "pisque" no failover (o blob guardado é o MESMO ciphertext do disco; a chave
    Fernet nunca vai para o banco). Espelha o padrão least-privilege de `feedback.py`.

Espelha a lógica de refresh de `calculadora_crefaz.auth.carregar_sessao_existente`:
se o access token expirou e há refresh_token, renova e regrava.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from cryptography.fernet import Fernet, InvalidToken
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from calculadora_crefaz.auth_core import SessaoAutenticada
from calculadora_crefaz.config import OAUTH_SCOPES

from .settings import get_settings

logger = logging.getLogger(__name__)

_SUPABASE_TIMEOUT = 10.0


def _fernet() -> Fernet:
    s = get_settings()
    if s.token_enc_key:
        return Fernet(s.token_enc_key.encode())
    # Deriva uma chave Fernet (32 bytes urlsafe-b64) do SESSION_SECRET.
    chave = base64.urlsafe_b64encode(hashlib.sha256(s.session_secret.encode()).digest())
    return Fernet(chave)


def _email_hash(email: str) -> str:
    return hashlib.sha256(email.lower().encode()).hexdigest()


# ─────────────────────────── backend: disco ───────────────────────────

def _dir() -> Path:
    d = get_settings().token_store_path
    d.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(d, 0o700)
    except OSError:
        pass
    return d


def _path_for(email: str) -> Path:
    return _dir() / f"{_email_hash(email)}.enc"


def _disk_read(email: str) -> Optional[bytes]:
    caminho = _path_for(email)
    if not caminho.exists():
        return None
    return caminho.read_bytes()


def _disk_write(email: str, blob: bytes) -> None:
    caminho = _path_for(email)
    caminho.write_bytes(blob)
    try:
        os.chmod(caminho, 0o600)
    except OSError:
        pass


def _disk_delete(email: str) -> None:
    try:
        _path_for(email).unlink()
    except FileNotFoundError:
        pass


# ────────────────────────── backend: supabase ──────────────────────────

def _sb_url(s) -> str:
    return f"{s.supabase_url}/rest/v1/{s.oauth_table}"


def _sb_headers(s, *, prefer: str | None = None) -> dict:
    h = {
        "apikey": s.supabase_anon_key,
        "Authorization": f"Bearer {s.supabase_anon_key}",
        "Content-Type": "application/json",
    }
    if prefer:
        h["Prefer"] = prefer
    return h


def _sb_read(email: str) -> Optional[bytes]:
    """Lê o ciphertext no Supabase. None se ausente OU em falha (degrada p/ re-auth)."""
    s = get_settings()
    params = {"email_hash": f"eq.{_email_hash(email)}", "select": "encrypted_creds"}
    try:
        with httpx.Client(timeout=_SUPABASE_TIMEOUT) as client:
            resp = client.get(_sb_url(s), headers=_sb_headers(s), params=params)
        if resp.status_code != 200:
            logger.error("token_store supabase read %s: %s", resp.status_code, resp.text[:300])
            return None
        rows = resp.json()
        if not rows:
            return None
        return rows[0]["encrypted_creds"].encode()
    except Exception as e:  # noqa: BLE001 — falha de rede não deve derrubar o request
        logger.warning("token_store supabase read falhou para %s: %s", email, e)
        return None


def _sb_write(email: str, blob: bytes) -> None:
    """UPSERT do ciphertext. Levanta em falha (save deve ser visível)."""
    s = get_settings()
    row = {
        "email_hash": _email_hash(email),
        "encrypted_creds": blob.decode(),  # Fernet = ascii urlsafe-b64
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    headers = _sb_headers(s, prefer="resolution=merge-duplicates,return=minimal")
    with httpx.Client(timeout=_SUPABASE_TIMEOUT) as client:
        resp = client.post(_sb_url(s), headers=headers, json=row)
    if resp.status_code not in (200, 201, 204):
        logger.error("token_store supabase write %s: %s", resp.status_code, resp.text[:300])
        raise RuntimeError(f"Falha ao gravar token no Supabase (HTTP {resp.status_code}).")


def _sb_delete(email: str) -> None:
    s = get_settings()
    params = {"email_hash": f"eq.{_email_hash(email)}"}
    try:
        with httpx.Client(timeout=_SUPABASE_TIMEOUT) as client:
            resp = client.delete(_sb_url(s), headers=_sb_headers(s, prefer="return=minimal"), params=params)
        if resp.status_code not in (200, 204):
            logger.error("token_store supabase delete %s: %s", resp.status_code, resp.text[:300])
    except Exception as e:  # noqa: BLE001 — logout não deve quebrar por falha de rede
        logger.warning("token_store supabase delete falhou para %s: %s", email, e)


# ─────────────────────────── API pública ───────────────────────────

def save(email: str, creds: Credentials) -> None:
    blob = _fernet().encrypt(creds.to_json().encode())
    if get_settings().token_store_supabase:
        _sb_write(email, blob)
    else:
        _disk_write(email, blob)


def delete(email: str) -> None:
    if get_settings().token_store_supabase:
        _sb_delete(email)
    else:
        _disk_delete(email)


def load(email: str) -> Optional[Credentials]:
    """Carrega credenciais cifradas; faz refresh se expirado. None se inválido/ausente."""
    blob = _sb_read(email) if get_settings().token_store_supabase else _disk_read(email)
    if blob is None:
        return None
    try:
        raw = _fernet().decrypt(blob)
    except InvalidToken:
        logger.warning("Token cifrado inválido para %s (chave trocada?).", email)
        return None

    creds = Credentials.from_authorized_user_info(json.loads(raw), OAUTH_SCOPES)

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            save(email, creds)
        except Exception as e:  # noqa: BLE001 — qualquer falha de refresh = sessão inválida
            logger.warning("Falha ao renovar token de %s: %s", email, e)
            return None

    if not creds.valid:
        return None
    return creds


def carregar_sessao(email: str) -> Optional[SessaoAutenticada]:
    """Conveniência: Credentials válidas → SessaoAutenticada (o que o pipeline espera)."""
    creds = load(email)
    if not creds:
        return None
    return SessaoAutenticada(credentials=creds, email=email)
