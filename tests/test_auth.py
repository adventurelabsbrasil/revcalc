"""Testes do módulo auth — focados em validações puras (domínio, .env, helpers).

Os fluxos OAuth de fato (browser + loopback) só rodam manualmente — não há
mocks decentes para `flow.run_local_server`. Cobertura E2E vem do smoke test.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from calculadora_crefaz.auth import (
    _carregar_client_id,
    _username_para_email,
    _validar_dominio,
)
from calculadora_crefaz.exceptions import AuthError


def test_validar_dominio_rose():
    _validar_dominio("bruna@roseportaladvocacia.com.br")  # não levanta


def test_validar_dominio_adventure():
    _validar_dominio("contato@adventurelabs.com.br")  # não levanta


def test_validar_dominio_estranho_bloqueia():
    with pytest.raises(AuthError) as exc:
        _validar_dominio("alguem@gmail.com")
    assert "gmail.com" in str(exc.value)


def test_validar_dominio_case_insensitive():
    _validar_dominio("BRUNA@RosePortalAdvocacia.com.br")  # não levanta


def test_username_para_email_estavel():
    u = _username_para_email("bruna@roseportaladvocacia.com.br")
    assert u == "oauth-tokens-bruna@roseportaladvocacia.com.br"
    # idempotente
    assert u == _username_para_email("bruna@roseportaladvocacia.com.br")


def test_carregar_client_id_de_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "test-id-from-env.apps.googleusercontent.com")
    assert _carregar_client_id() == "test-id-from-env.apps.googleusercontent.com"


def test_carregar_client_id_falha_se_ausente(monkeypatch, tmp_path):
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_ID", raising=False)
    # Apontar __file__ pra um diretório sem .env
    import calculadora_crefaz.auth as auth_module

    fake_module = tmp_path / "fake.py"
    fake_module.touch()
    # Não tem .env em tmp_path
    monkeypatch.setattr(auth_module, "__file__", str(fake_module / "src" / "calculadora_crefaz" / "auth.py"))
    with pytest.raises(AuthError) as exc:
        _carregar_client_id()
    assert "GOOGLE_OAUTH_CLIENT_ID" in str(exc.value)


def test_carregar_client_id_de_dotenv(monkeypatch, tmp_path):
    """Simula um .env na raiz do projeto."""
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_ID", raising=False)

    # Criar estrutura tmp/projeto/src/calculadora_crefaz/auth.py + tmp/projeto/.env
    proj = tmp_path / "projeto"
    src_module = proj / "src" / "calculadora_crefaz"
    src_module.mkdir(parents=True)
    (src_module / "auth.py").touch()
    (proj / ".env").write_text("GOOGLE_OAUTH_CLIENT_ID=from-dotenv-id.apps.googleusercontent.com\n")

    import calculadora_crefaz.auth as auth_module

    monkeypatch.setattr(auth_module, "__file__", str(src_module / "auth.py"))
    assert _carregar_client_id() == "from-dotenv-id.apps.googleusercontent.com"
