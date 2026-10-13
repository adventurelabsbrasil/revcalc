"""Local configuration for managed desktop installations; never fetches a backend.

The deployment profile contains public OAuth identification and tenant metadata,
not credentials. It is delivered through the administrator's installation kit.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from .exceptions import AuthError

PROFILE_NAME = "revcalc-desktop.json"
PROFILE_KEYS = {
    "schema_version", "client_type", "desktop_client_id", "allowed_domains",
    "drive_root_id", "bacen_folder_id", "bacen_new_folder_id",
}
DOMAIN_RE = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}")


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def read_dotenv(name: str, root: Path | None = None) -> str | None:
    explicit = os.environ.get("REVCALC_ENV_PATH")
    path = Path(explicit) if explicit else (root or project_root()) / ".env"
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == name:
            return value.strip().strip('"').strip("'") or None
    return None


def profile_path() -> Path | None:
    explicit = os.environ.get("REVCALC_PROFILE_PATH")
    if explicit:
        return Path(explicit)
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        persistent = Path(os.environ["LOCALAPPDATA"]) / "AdventureLabs" / "RevCalc" / "config" / PROFILE_NAME
        if persistent.is_file():
            return persistent
    adjacent = project_root() / PROFILE_NAME
    if adjacent.is_file():
        return adjacent
    if hasattr(sys, "_MEIPASS"):
        bundled = Path(sys._MEIPASS) / PROFILE_NAME
        if bundled.is_file():
            return bundled
    return None


def validate_profile(data: object) -> dict:
    if not isinstance(data, dict) or set(data) - PROFILE_KEYS:
        raise AuthError("Perfil desktop inválido: campos desconhecidos ou confidenciais.")
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1 or data.get("client_type") != "desktop":
        raise AuthError("Perfil desktop inválido: versão ou tipo de cliente OAuth.")
    cid = data.get("desktop_client_id")
    if not isinstance(cid, str) or not re.fullmatch(r"[A-Za-z0-9-]+\.apps\.googleusercontent\.com", cid):
        raise AuthError("Perfil desktop inválido: Client ID.")
    domains = data.get("allowed_domains")
    if not isinstance(domains, list) or not domains or any(
        not isinstance(d, str) or not DOMAIN_RE.fullmatch(d.lower()) for d in domains
    ):
        raise AuthError("Perfil desktop inválido: domínios autorizados.")
    for key in ("drive_root_id", "bacen_folder_id", "bacen_new_folder_id"):
        value = data.get(key)
        if key == "bacen_new_folder_id" and value is None:
            continue
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise AuthError("Perfil desktop inválido: referências do Drive.")
    return data


def load_profile() -> dict:
    path = profile_path()
    if path is None:
        return {}
    try:
        return validate_profile(json.loads(path.read_text(encoding="utf-8-sig")))
    except (OSError, ValueError) as exc:
        raise AuthError("Não foi possível ler o perfil desktop. Reinstale o kit fornecido pela Adventure.") from exc


def setting(name: str, default: str = "", profile_key: str | None = None) -> str:
    # Legacy values keep precedence; profiles never overwrite deployed secrets.
    value = os.environ.get(name)
    if value is not None:
        return value.strip()
    value = read_dotenv(name)
    if value is not None:
        return value
    if profile_key:
        value = load_profile().get(profile_key)
        if isinstance(value, list):
            return ",".join(value)
        if value is not None:
            return str(value)
    return default


def main() -> None:
    """Installer validation: no credential values are printed."""
    load_profile()
    from .auth import _carregar_client_id

    _carregar_client_id()


if __name__ == "__main__":
    main()
