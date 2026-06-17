"""Configuração do backend via ambiente.

Lê variáveis de ambiente (e um .env na raiz do repo em dev). Não instancia nada
no import — use `get_settings()` (cacheado) para que importar o pacote em teste
não exija o ambiente completo.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _load_dotenv() -> None:
    """Carrega um .env (raiz do repo ou cwd) em dev — não sobrescreve env já setado."""
    candidatos = [Path.cwd() / ".env", Path(__file__).resolve().parents[1] / ".env"]
    for env_path in candidatos:
        if not env_path.exists():
            continue
        for linha in env_path.read_text().splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, valor = linha.split("=", 1)
            os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))
        break


def _req(nome: str) -> str:
    val = os.environ.get(nome)
    if not val:
        raise RuntimeError(
            f"Env var obrigatória ausente: {nome}. "
            "Defina no ambiente do container ou no .env (ver .env.example)."
        )
    return val


@dataclass(frozen=True)
class Settings:
    client_id: str
    client_secret: str
    redirect_uri: str          # https://api.revcalc.<dominio>/api/auth/callback
    frontend_origin: str       # https://revcalc.<dominio>  (origem do front, p/ CORS + redirect)
    session_secret: str        # segredo p/ assinar cookie de sessão + stream token
    token_store_path: Path     # diretório do token store cifrado (volume)
    token_enc_key: str | None  # chave Fernet opcional; se ausente, derivada do session_secret
    cookie_name: str
    cookie_domain: str | None  # ".adventurelabs.com.br" p/ cookie first-party entre subdomínios
    cookie_samesite: str       # "lax" (mesmo site/subdomínio) ou "none" (cross-site)
    cookie_secure: bool
    # Feedback (opcional) — se ausente, o endpoint /api/feedback responde 503 e o app
    # segue funcionando. Insere em public.revcalc_feedback via PostgREST + ANON key
    # (least-privilege: INSERT-only via RLS; a service_role NÃO vive aqui).
    supabase_url: str | None
    supabase_anon_key: str | None
    feedback_table: str
    # Notificação ao Founder (opcional) — WhatsApp via Evolution API. Se ausente, o
    # feedback grava normalmente e o alerta é no-op (notify_enabled = False). Destino
    # aceita número ou JID de grupo (grupo "Comando Estelar" = ...@g.us).
    evolution_api_url: str | None
    evolution_api_key: str | None
    evolution_instance: str
    founder_notify_wa: tuple[str, ...]
    notify_cliente: str

    @property
    def feedback_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_anon_key)

    @property
    def notify_enabled(self) -> bool:
        return bool(self.evolution_api_url and self.evolution_api_key and self.founder_notify_wa)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_dotenv()
    return Settings(
        client_id=_req("GOOGLE_OAUTH_CLIENT_ID"),
        client_secret=_req("GOOGLE_OAUTH_CLIENT_SECRET"),
        redirect_uri=_req("OAUTH_REDIRECT_URI"),
        frontend_origin=_req("FRONTEND_ORIGIN").rstrip("/"),
        session_secret=_req("SESSION_SECRET"),
        token_store_path=Path(os.environ.get("TOKEN_STORE_PATH", "/data/tokens")),
        token_enc_key=os.environ.get("TOKEN_ENC_KEY") or None,
        cookie_name=os.environ.get("COOKIE_NAME", "revcalc_session"),
        cookie_domain=(os.environ.get("COOKIE_DOMAIN") or "").strip() or None,
        cookie_samesite=os.environ.get("COOKIE_SAMESITE", "lax").strip().lower(),
        cookie_secure=os.environ.get("COOKIE_SECURE", "true").strip().lower() != "false",
        supabase_url=(os.environ.get("SUPABASE_URL") or "").strip().rstrip("/") or None,
        supabase_anon_key=(os.environ.get("SUPABASE_ANON_KEY") or "").strip() or None,
        feedback_table=os.environ.get("REVCALC_FEEDBACK_TABLE", "revcalc_feedback").strip(),
        evolution_api_url=(os.environ.get("EVOLUTION_API_URL") or "").strip().rstrip("/") or None,
        evolution_api_key=(os.environ.get("EVOLUTION_API_KEY") or "").strip() or None,
        evolution_instance=(os.environ.get("EVOLUTION_INSTANCE") or "adventure").strip() or "adventure",
        founder_notify_wa=tuple(
            n.strip()
            for n in re.split(r"[;,]", os.environ.get("REVCALC_FOUNDER_NOTIFY_WA", ""))
            if n.strip()
        ),
        notify_cliente=(os.environ.get("REVCALC_NOTIFY_CLIENTE") or "Rose Portal Advocacia").strip(),
    )
