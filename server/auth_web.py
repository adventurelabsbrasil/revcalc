"""OAuth web server-side (substitui o loopback desktop do auth.py).

Fluxo authorization-code com redirect_uri fixo. Reaproveita a validação de
domínio e a extração de email do pacote desktop (auth_core, sem keyring).
Também centraliza a assinatura de:
  - cookie de sessão (email logado)         — salt "session"
  - state anti-CSRF do OAuth                  — salt "oauth-state"
  - stream token do SSE (run_id + email)      — salt "stream" (EventSource não manda header)
"""

from __future__ import annotations

import os
from typing import Optional

from google_auth_oauthlib.flow import Flow
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from calculadora_crefaz.auth_core import _email_do_token, _validar_dominio
from calculadora_crefaz.config import OAUTH_SCOPES

from .settings import get_settings

# O Google costuma devolver escopos extras (openid) — relaxa a checagem do oauthlib.
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

SESSION_MAX_AGE = 60 * 60 * 24 * 14   # 14 dias
STATE_MAX_AGE = 60 * 10               # 10 min p/ completar o consent
STREAM_MAX_AGE = 60 * 10             # 10 min p/ abrir o SSE após o POST /run


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().session_secret)


def _web_client_config() -> dict:
    s = get_settings()
    return {
        "web": {
            "client_id": s.client_id,
            "client_secret": s.client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [s.redirect_uri],
        }
    }


def _flow(state: Optional[str] = None) -> Flow:
    return Flow.from_client_config(
        _web_client_config(),
        scopes=OAUTH_SCOPES,
        redirect_uri=get_settings().redirect_uri,
        state=state,
    )


def authorization_url() -> tuple[str, str]:
    """URL de consent do Google + o `state` (a guardar em cookie p/ validar no callback)."""
    auth_url, state = _flow().authorization_url(
        access_type="offline",        # garante refresh_token
        include_granted_scopes="true",
        prompt="consent",             # força emissão de refresh_token
    )
    return auth_url, state


def trocar_code(code: str, state: Optional[str] = None):
    """Troca o authorization code por credenciais; valida domínio. Retorna (email, creds)."""
    flow = _flow(state=state)
    flow.fetch_token(code=code)
    creds = flow.credentials
    email = _email_do_token(creds)
    _validar_dominio(email)  # levanta AuthError se domínio não autorizado
    return email, creds


# ─── Assinaturas (cookies / tokens) ─────────────────────────────────────────

def assinar_sessao(email: str) -> str:
    return _serializer().dumps(email, salt="session")


def ler_sessao(token: str) -> Optional[str]:
    try:
        return _serializer().loads(token, salt="session", max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def assinar_state(state: str) -> str:
    return _serializer().dumps(state, salt="oauth-state")


def ler_state(token: str) -> Optional[str]:
    try:
        return _serializer().loads(token, salt="oauth-state", max_age=STATE_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def assinar_stream_token(run_id: str, email: str) -> str:
    return _serializer().dumps({"run_id": run_id, "email": email}, salt="stream")


def ler_stream_token(token: str) -> Optional[dict]:
    try:
        return _serializer().loads(token, salt="stream", max_age=STREAM_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
