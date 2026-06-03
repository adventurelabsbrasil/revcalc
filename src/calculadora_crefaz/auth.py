"""OAuth desktop flow + token persistido em keyring.

Não usa client_secret — apenas client_id + PKCE + loopback redirect.
Restringe login aos domínios autorizados (Rose + Adventure).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

import keyring
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# SessaoAutenticada / _email_do_token / _validar_dominio vivem em auth_core (sem
# keyring) e são re-exportados aqui para compatibilidade com imports existentes.
from .auth_core import SessaoAutenticada, _email_do_token, _validar_dominio
from .config import KEYRING_SERVICE, OAUTH_SCOPES
from .exceptions import AuthError

__all__ = [
    "SessaoAutenticada",
    "_email_do_token",
    "_validar_dominio",
    "carregar_sessao_existente",
    "fluxo_login",
    "logout",
    "ultimo_email_logado",
]

logger = logging.getLogger(__name__)


def _carregar_var(nome: str) -> Optional[str]:
    """Lê variável do ambiente ou de .env na raiz do projeto."""
    val = os.environ.get(nome)
    if val:
        return val

    raiz = Path(__file__).resolve().parents[2]
    env_path = raiz / ".env"
    if env_path.exists():
        for linha in env_path.read_text().splitlines():
            linha = linha.strip()
            if linha.startswith(f"{nome}="):
                return linha.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def _carregar_client_id() -> str:
    cid = _carregar_var("GOOGLE_OAUTH_CLIENT_ID")
    if not cid:
        raise AuthError(
            "GOOGLE_OAUTH_CLIENT_ID não definido. "
            "Defina via env var ou em .env na raiz do projeto."
        )
    return cid


def _carregar_client_secret() -> str:
    cs = _carregar_var("GOOGLE_OAUTH_CLIENT_SECRET")
    if not cs:
        raise AuthError(
            "GOOGLE_OAUTH_CLIENT_SECRET não definido. "
            "Pegue no Google Cloud Console (Credentials > OAuth 2.0 Client IDs) "
            "e adicione ao .env."
        )
    return cs


def _client_config(client_id: str, client_secret: str) -> dict:
    """Monta o dict que o InstalledAppFlow espera."""
    return {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }


def _username_para_email(email: str) -> str:
    return f"oauth-tokens-{email}"


def _salvar_token(email: str, creds: Credentials) -> None:
    payload = creds.to_json()
    keyring.set_password(KEYRING_SERVICE, _username_para_email(email), payload)
    # Salva também o último email logado, pra próxima abertura saber qual buscar
    keyring.set_password(KEYRING_SERVICE, "ultimo-email", email)


def _carregar_token(email: str) -> Optional[Credentials]:
    raw = keyring.get_password(KEYRING_SERVICE, _username_para_email(email))
    if not raw:
        return None
    return Credentials.from_authorized_user_info(json.loads(raw), OAUTH_SCOPES)


def ultimo_email_logado() -> Optional[str]:
    return keyring.get_password(KEYRING_SERVICE, "ultimo-email")


def carregar_sessao_existente() -> Optional[SessaoAutenticada]:
    """Tenta carregar token salvo do último email logado.

    Faz refresh automático se expirado. Retorna None se não há token válido.
    """
    email = ultimo_email_logado()
    if not email:
        return None

    creds = _carregar_token(email)
    if not creds:
        return None

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _salvar_token(email, creds)
        except Exception as e:
            logger.warning("Falha ao renovar token: %s", e)
            return None

    if not creds.valid:
        return None

    return SessaoAutenticada(credentials=creds, email=email)


def fluxo_login() -> SessaoAutenticada:
    """Inicia loopback OAuth flow. Abre browser, aguarda redirect.

    Valida domínio do email retornado e persiste token no keyring.
    """
    client_id = _carregar_client_id()
    client_secret = _carregar_client_secret()
    flow = InstalledAppFlow.from_client_config(
        _client_config(client_id, client_secret),
        scopes=OAUTH_SCOPES,
    )
    # run_local_server abre browser, sobe servidor loopback em porta randômica,
    # captura o redirect com o code, troca por tokens
    creds = flow.run_local_server(
        port=0,  # porta randômica
        open_browser=True,
        success_message=(
            "Autenticação concluída. Você pode fechar esta aba e voltar ao app."
        ),
    )

    email = _email_do_token(creds)
    _validar_dominio(email)
    _salvar_token(email, creds)

    return SessaoAutenticada(credentials=creds, email=email)


def logout(email: Optional[str] = None) -> None:
    """Remove token salvo do keyring."""
    email = email or ultimo_email_logado()
    if not email:
        return
    try:
        keyring.delete_password(KEYRING_SERVICE, _username_para_email(email))
    except keyring.errors.PasswordDeleteError:
        pass
    try:
        keyring.delete_password(KEYRING_SERVICE, "ultimo-email")
    except keyring.errors.PasswordDeleteError:
        pass
