import json

import pytest

from calculadora_crefaz import auth, desktop_config
from calculadora_crefaz.auth_core import _validar_dominio
from calculadora_crefaz.exceptions import AuthError


def profile():
    return {
        "schema_version": 1, "client_type": "desktop",
        "desktop_client_id": "123-test.apps.googleusercontent.com",
        "allowed_domains": ["example.invalid", "adventurelabs.com.br"],
        "drive_root_id": "ROOT_TEST", "bacen_folder_id": "BACEN_TEST",
    }


@pytest.fixture
def configured(monkeypatch, tmp_path):
    path = tmp_path / "revcalc-desktop.json"
    path.write_text(json.dumps(profile()), encoding="utf-8-sig")
    monkeypatch.setenv("REVCALC_PROFILE_PATH", str(path))
    monkeypatch.setattr(desktop_config, "project_root", lambda: tmp_path)
    return path


def test_profile_id_does_not_reuse_web_secret(configured, monkeypatch):
    monkeypatch.delenv("GOOGLE_OAUTH_DESKTOP_CLIENT_ID", raising=False)
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "web-client-id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "web-confidential-secret")
    assert auth._carregar_client_id() == profile()["desktop_client_id"]
    assert auth._carregar_client_secret() == ""


def test_profile_settings_and_legacy_precedence(configured, monkeypatch):
    monkeypatch.delenv("REVCALC_PASTA_MAE_ID", raising=False)
    assert desktop_config.setting("REVCALC_PASTA_MAE_ID", profile_key="drive_root_id") == "ROOT_TEST"
    (configured.parent / ".env").write_text("REVCALC_PASTA_MAE_ID=LEGACY_ROOT\n", encoding="utf-8-sig")
    assert desktop_config.setting("REVCALC_PASTA_MAE_ID", profile_key="drive_root_id") == "LEGACY_ROOT"
    monkeypatch.setenv("REVCALC_PASTA_MAE_ID", "ENV_ROOT")
    assert desktop_config.setting("REVCALC_PASTA_MAE_ID", profile_key="drive_root_id") == "ENV_ROOT"


@pytest.mark.parametrize("change", [
    {"client_secret": "never-distribute"}, {"client_type": "web"},
    {"schema_version": True}, {"schema_version": 2},
    {"desktop_client_id": "placeholder"}, {"allowed_domains": []},
    {"allowed_domains": ["*.example.invalid"]}, {"allowed_domains": ["example.invalid/path"]},
    {"drive_root_id": ""},
])
def test_profile_rejects_incomplete_or_confidential_data(change):
    with pytest.raises(AuthError):
        desktop_config.validate_profile(profile() | change)


def test_explicit_missing_profile_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setenv("REVCALC_PROFILE_PATH", str(tmp_path / "missing.json"))
    with pytest.raises(AuthError):
        desktop_config.load_profile()


@pytest.mark.parametrize("email", ["adventurelabs.com.br", "x@@adventurelabs.com.br", "x@sub.adventurelabs.com.br", "x@adventurelabs.com.br.attacker.invalid", " x@adventurelabs.com.br"])
def test_exact_domain_and_email_syntax(email):
    with pytest.raises(AuthError):
        _validar_dominio(email)


def test_tenant_domain_is_data_not_public_code(configured, monkeypatch):
    import calculadora_crefaz.auth_core as core
    data = profile() | {"allowed_domains": ["client.example"]}
    configured.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(core, "DOMINIOS_PERMITIDOS", tuple(desktop_config.load_profile()["allowed_domains"]))
    core._validar_dominio("user@client.example")
    with pytest.raises(AuthError):
        core._validar_dominio("user@adventurelabs.com.br")


def test_frozen_exe_resolves_adjacent_configuration(monkeypatch, tmp_path):
    monkeypatch.setattr(desktop_config.sys, "frozen", True, raising=False)
    monkeypatch.setattr(desktop_config.sys, "executable", str(tmp_path / "RevCalc.exe"))
    # Use the real resolver rather than the configured fixture.
    assert desktop_config.project_root() == tmp_path
