"""Token store server-side, cifrado em volume (substitui o keyring desktop).

Um arquivo por email (`<sha256(email)>.enc`), conteúdo = Fernet(creds.to_json()).
A chave Fernet vem de TOKEN_ENC_KEY ou é derivada do SESSION_SECRET. O token
NUNCA vai para o browser — o front só carrega um cookie de sessão opaco.

Espelha a lógica de refresh de `calculadora_crefaz.auth.carregar_sessao_existente`:
se o access token expirou e há refresh_token, renova e regrava.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from calculadora_crefaz.auth_core import SessaoAutenticada
from calculadora_crefaz.config import OAUTH_SCOPES

from .settings import get_settings

logger = logging.getLogger(__name__)


def _fernet() -> Fernet:
    s = get_settings()
    if s.token_enc_key:
        return Fernet(s.token_enc_key.encode())
    # Deriva uma chave Fernet (32 bytes urlsafe-b64) do SESSION_SECRET.
    chave = base64.urlsafe_b64encode(hashlib.sha256(s.session_secret.encode()).digest())
    return Fernet(chave)


def _dir() -> Path:
    d = get_settings().token_store_path
    d.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(d, 0o700)
    except OSError:
        pass
    return d


def _path_for(email: str) -> Path:
    nome = hashlib.sha256(email.lower().encode()).hexdigest()
    return _dir() / f"{nome}.enc"


def save(email: str, creds: Credentials) -> None:
    blob = _fernet().encrypt(creds.to_json().encode())
    caminho = _path_for(email)
    caminho.write_bytes(blob)
    try:
        os.chmod(caminho, 0o600)
    except OSError:
        pass


def delete(email: str) -> None:
    try:
        _path_for(email).unlink()
    except FileNotFoundError:
        pass


def load(email: str) -> Optional[Credentials]:
    """Carrega credenciais cifradas; faz refresh se expirado. None se inválido/ausente."""
    caminho = _path_for(email)
    if not caminho.exists():
        return None
    try:
        raw = _fernet().decrypt(caminho.read_bytes())
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
