"""Verificações antes de subir a UI — mensagens claras no terminal (sem stack cru).

Executadas apenas em modo desenvolvimento (`python -m calculadora_crefaz`).
No bundle PyInstaller (`sys.frozen`), não bloqueia — dependências já embutidas.
"""

from __future__ import annotations

import importlib
import os
import shutil
import sys


MIN_PYTHON = (3, 11)

# (import_module_path, pip_hint ou None se stdlib / especial)
_DEPS: tuple[tuple[str, str | None, str | None], ...] = (
    ("tkinter", None, "Linux: sudo apt install python3-tk"),
    ("google.oauth2.credentials", "google-auth-oauthlib", None),
    ("googleapiclient.discovery", "google-api-python-client", None),
    ("google_auth_oauthlib.flow", "google-auth-oauthlib", None),
    ("openpyxl", "openpyxl", None),
    ("pdfplumber", "pdfplumber", None),
    ("httpx", "httpx", None),
    ("rapidfuzz", "rapidfuzz", None),
    ("unidecode", "Unidecode", None),
    ("dateutil", "python-dateutil", None),
    ("keyring", "keyring", None),
    ("pypdfium2", "pypdfium2", None),
    ("PIL", "Pillow", None),
)


def _is_bundle() -> bool:
    return getattr(sys, "frozen", False)


def _skip_preflight() -> bool:
    return _is_bundle() or os.environ.get("REVCALC_SKIP_PREFLIGHT", "").strip() == "1"


def _banner_stderr() -> None:
    if not sys.stderr.isatty():
        return
    try:
        from . import __version__
    except Exception:
        __version__ = "?"
    linha = "=" * 60
    print(linha, file=sys.stderr)
    print(f" Calculadora Crefaz · v{__version__}", file=sys.stderr)
    print(" Rose Portal Advocacia · desenvolvido pela Adventure Labs", file=sys.stderr)
    print(linha, file=sys.stderr)


def _hint_windows_python() -> str:
    return (
        "\n─── Windows / Python não encontrado ───\n"
        "• Instale Python 3.11 ou mais novo: https://www.python.org/downloads/windows/\n"
        "  Na primeira tela do instalador, marque **Add python.exe to PATH**.\n"
        "• Ou pelo winget (CMD como Administrador):\n"
        "    winget install Python.Python.3.12\n"
        "• Feche e **abra de novo** o terminal e confira:\n"
        "    py --version\n"
        "    ou\n"
        "    python --version\n"
    )


def _hint_pip_install_projeto() -> str:
    return (
        "\n─── Corrigir dependências ───\n"
        "Na pasta do projeto, com o ambiente virtual **ativado**:\n"
        "    pip install -U pip\n"
        "    pip install -e \".[dev]\"\n"
    )


def verificar_ou_sair() -> None:
    """Imprime ajuda em stderr e sai com código 1 se algo estiver faltando."""
    if _skip_preflight():
        return

    _banner_stderr()

    if sys.version_info < MIN_PYTHON:
        print(
            f"Erro: Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ é obrigatório. "
            f"Este interpretador é {sys.version.split()[0]}.\n",
            file=sys.stderr,
        )
        print(_hint_windows_python(), file=sys.stderr)
        sys.exit(1)

    faltando: list[tuple[str, str | None, str | None]] = []
    for modulo, pip_pkg, extra_hint in _DEPS:
        try:
            importlib.import_module(modulo)
        except ImportError as e:
            faltando.append((modulo, pip_pkg, extra_hint))
            # mantém primeiro erro para debug
            _ = e

    if faltando:
        print(
            "Erro: faltam pacotes Python necessários para a Calculadora Crefaz.\n",
            file=sys.stderr,
        )
        for modulo, pip_pkg, extra_hint in faltando:
            linha = f"  • `{modulo}`"
            if pip_pkg:
                linha += f" → pip install {pip_pkg}"
            print(linha, file=sys.stderr)
            if extra_hint and sys.platform.startswith("linux"):
                print(f"    ({extra_hint})", file=sys.stderr)
        print(_hint_pip_install_projeto(), file=sys.stderr)
        print(_hint_windows_python(), file=sys.stderr)
        sys.exit(1)

    # LibreOffice: não é fatal — só aviso
    if sys.stderr.isatty():
        if not shutil.which("soffice") and not shutil.which("libreoffice"):
            print(
                "\nAviso: LibreOffice (`soffice`) não está no PATH.\n"
                "O app gera XLSX e log, mas as capturas **13 Print** podem não sair.\n"
                "Windows: winget install --id TheDocumentFoundation.LibreOffice -e\n",
                file=sys.stderr,
            )
