import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_powershell_scripts_use_utf8_bom():
    for path in (ROOT / "cliente-kit").glob("*.ps1"):
        assert path.read_bytes().startswith(b"\xef\xbb\xbf"), path.name


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell 5.1 integration")
def test_windows_powershell_migration_reinstall_and_failure(tmp_path):
    powershell = shutil.which("powershell.exe")
    assert powershell
    result = subprocess.run([
        powershell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
        "-File", str(ROOT / "tests/windows/install-smoke.ps1"),
        "-Scratch", str(tmp_path), "-ModulePath", str(ROOT / "cliente-kit/RevCalc-Installation.ps1"),
    ], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "preservation OK" in result.stdout


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell parser")
def test_windows_powershell_51_parses_all_scripts():
    script = """
$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -ne 5) { throw 'Expected Windows PowerShell 5.1' }
Get-ChildItem -LiteralPath 'cliente-kit' -Filter '*.ps1' | ForEach-Object {
    $tokens = $null; $parseErrors = $null
    [System.Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$tokens, [ref]$parseErrors) | Out-Null
    if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
}
"""
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script], cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
