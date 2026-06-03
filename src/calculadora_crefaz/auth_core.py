"""Helpers de auth puros — SEM dependência de keyring/desktop.

Extraídos de auth.py para que o backend web (server/) possa reusar
`SessaoAutenticada`, `_email_do_token` e `_validar_dominio` sem importar
`keyring` (que é específico do fluxo desktop e exige backend de credenciais
do SO). auth.py re-exporta estes nomes para manter compatibilidade.
"""

from __future__ import annotations

from dataclasses import dataclass

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .config import DOMINIOS_PERMITIDOS
from .exceptions import AuthError


@dataclass
class SessaoAutenticada:
    """Wrap das credenciais + email do usuário logado."""

    credentials: Credentials
    email: str

    def drive_service(self):
        return build("drive", "v3", credentials=self.credentials, cache_discovery=False)


def _email_do_token(creds: Credentials) -> str:
    """Pega o email associado às credenciais via userinfo do Drive (about endpoint)."""
    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    about = service.about().get(fields="user(emailAddress)").execute()
    return about["user"]["emailAddress"]


def _validar_dominio(email: str) -> None:
    dominio = email.split("@", 1)[-1].lower()
    if dominio not in DOMINIOS_PERMITIDOS:
        raise AuthError(
            f"Domínio '{dominio}' não autorizado. "
            f"Permitidos: {', '.join(DOMINIOS_PERMITIDOS)}."
        )
