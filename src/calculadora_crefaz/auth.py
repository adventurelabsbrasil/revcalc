"""OAuth desktop flow + token persistido em keyring.

Perfil Desktop usa client_id + PKCE + loopback, sem segredo confidencial.
Preserva registros legados e restringe login à política do tenant.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from functools import partial
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
from .desktop_config import load_profile, read_dotenv, project_root

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

    raiz = project_root() if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[2]
    return read_dotenv(nome, raiz)


def _carregar_client_id() -> str:
    cid = (
        _carregar_var("GOOGLE_OAUTH_DESKTOP_CLIENT_ID")
        or load_profile().get("desktop_client_id")
        or _carregar_var("GOOGLE_OAUTH_CLIENT_ID")
    )
    if not cid:
        raise AuthError(
            "GOOGLE_OAUTH_CLIENT_ID não definido. "
            "Reinstale o kit com o perfil desktop fornecido pela Adventure. "
            "Em desenvolvimento, defina GOOGLE_OAUTH_DESKTOP_CLIENT_ID."
        )
    return cid


def _carregar_client_secret() -> str:
    # Preserve legacy desktop registrations. Never pair a web secret with a
    # dedicated desktop ID. Empty string bridges google-auth's None guard;
    # it is not a confidential credential and needs no user configuration.
    if _carregar_var("GOOGLE_OAUTH_DESKTOP_CLIENT_ID") or load_profile():
        return ""
    return _carregar_var("GOOGLE_OAUTH_CLIENT_SECRET") or ""


def _client_config(client_id: str, client_secret: str = "") -> dict:
    """Monta o dict que o InstalledAppFlow espera."""
    return {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://127.0.0.1"],
        }
    }


def _username_para_email(email: str) -> str:
    return f"oauth-tokens-{email}"


def _verificar_keyring() -> None:
    if sys.platform == "win32":
        from keyring.backends.Windows import WinVaultKeyring

        if not isinstance(keyring.get_keyring(), WinVaultKeyring):
            raise AuthError("Windows Credential Manager indisponível. Tokens não serão gravados em arquivos.")


def _validar_escopos(creds: Credentials) -> None:
    granted = creds.granted_scopes if creds.granted_scopes is not None else creds.scopes
    if isinstance(granted, str):
        granted = granted.split()
    if not set(OAUTH_SCOPES).issubset(set(granted or [])):
        raise AuthError("Autorize as permissões do Google Drive para usar o RevCalc.")


def _salvar_token(email: str, creds: Credentials) -> None:
    _verificar_keyring()
    payload = creds.to_json()
    keyring.set_password(KEYRING_SERVICE, _username_para_email(email), payload)
    # Salva também o último email logado, pra próxima abertura saber qual buscar
    keyring.set_password(KEYRING_SERVICE, "ultimo-email", email)


def _carregar_token(email: str) -> Optional[Credentials]:
    _verificar_keyring()
    raw = keyring.get_password(KEYRING_SERVICE, _username_para_email(email))
    if not raw:
        return None
    try:
        data = json.loads(raw)
        # New public-client tokens may omit client_secret; legacy tokens retain
        # their original client ID/secret so their refresh grant still works.
        data.setdefault("client_secret", "")
        return Credentials.from_authorized_user_info(data)
    except (ValueError, TypeError, AttributeError):
        logger.warning("Credencial salva inválida; novo login necessário.")
        return None


def ultimo_email_logado() -> Optional[str]:
    _verificar_keyring()
    return keyring.get_password(KEYRING_SERVICE, "ultimo-email")


def carregar_sessao_existente() -> Optional[SessaoAutenticada]:
    """Tenta carregar token salvo do último email logado.

    Faz refresh automático se expirado. Retorna None se não há token válido.
    """
    email = ultimo_email_logado()
    if not email:
        return None

    try:
        _validar_dominio(email)
    except AuthError:
        return None

    creds = _carregar_token(email)
    if not creds:
        return None

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            logger.warning("Falha ao renovar token; novo login necessário.")
            return None

    if not creds.valid:
        return None

    try:
        _validar_escopos(creds)
        identity = _email_do_token(creds)
        _validar_dominio(identity)
        if identity.lower() != email.lower():
            return None
    except Exception:
        logger.warning("Não foi possível validar a conta salva.")
        return None
    _salvar_token(email, creds)

    return SessaoAutenticada(credentials=creds, email=email)


def fluxo_login() -> SessaoAutenticada:
    """Inicia loopback OAuth flow. Abre browser, aguarda redirect.

    Valida domínio do email retornado e persiste token no keyring.
    """
    client_id = _carregar_client_id()
    _verificar_keyring()
    client_secret = _carregar_client_secret()
    flow = InstalledAppFlow.from_client_config(
        _client_config(client_id, client_secret),
        scopes=OAUTH_SCOPES,
        autogenerate_code_verifier=True,
    )
    # Public clients identify themselves in the token body, not HTTP Basic auth.
    flow.fetch_token = partial(flow.fetch_token, include_client_id=True)
    # run_local_server abre browser, sobe servidor loopback em porta randômica,
    # captura o redirect com o code, troca por tokens
    try:
        creds = flow.run_local_server(
            host="127.0.0.1",
            bind_addr="127.0.0.1",
            port=0,
            open_browser=True,
            timeout_seconds=180,
            authorization_prompt_message=None,
            success_message="Resposta recebida. Volte ao RevCalc para verificar o acesso.",
            access_type="offline",
            prompt="consent",
        )
    except Exception:
        # OAuth exceptions can contain authorization codes or token responses.
        raise AuthError("Login não concluído, cancelado ou expirado. Tente entrar novamente.") from None

    try:
        _validar_escopos(creds)
        if not creds.refresh_token:
            raise AuthError("Google não forneceu acesso persistente. Tente entrar novamente e confirme o consentimento.")
        email = _email_do_token(creds)
        _validar_dominio(email)
        _salvar_token(email, creds)
    except AuthError:
        raise
    except Exception:
        raise AuthError("Não foi possível validar ou salvar a conta. Tente entrar novamente.") from None

    return SessaoAutenticada(credentials=creds, email=email)


def logout(email: Optional[str] = None) -> None:
    """Remove token salvo do keyring."""
    email = email or ultimo_email_logado()
    if not email:
        return
    _verificar_keyring()
    try:
        keyring.delete_password(KEYRING_SERVICE, _username_para_email(email))
    except keyring.errors.PasswordDeleteError:
        pass
    try:
        keyring.delete_password(KEYRING_SERVICE, "ultimo-email")
    except keyring.errors.PasswordDeleteError:
        pass
