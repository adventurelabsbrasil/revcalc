# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — empacota o app num único .exe Windows.

Build no Windows:
    pyinstaller pyinstaller.spec

Output: dist/CalculadoraCrefaz.exe
"""

import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Caminho do projeto — onde mora o template
projeto_dir = os.path.abspath(os.path.dirname("__file__"))

datas = [
    # Embarca o template dentro do bundle
    ("templates/Calculo.xlsx", "templates"),
]

# google-api-python-client carrega arquivos JSON em runtime via discovery
datas += collect_data_files("googleapiclient")

a = Analysis(
    ["src/calculadora_crefaz/__main__.py"],
    pathex=["src"],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "keyring.backends.macOS",
        "keyring.backends.SecretService",
        "keyring.backends.Windows",
        "keyring.backends.kwallet",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclui módulos que não usamos pra reduzir tamanho do bundle
        "matplotlib",
        "numpy",
        "pandas",
        "PIL",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="CalculadoraCrefaz",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # --windowed: sem console no Windows
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
