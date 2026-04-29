"""Entry point: `python -m calculadora_crefaz` ou via PyInstaller."""

from .preflight import verificar_ou_sair


def main() -> None:
    verificar_ou_sair()
    from .ui import main as ui_main

    ui_main()


if __name__ == "__main__":
    main()
