param(
    [switch]$InstallLibreOffice,
    [string]$Version = "0.9.15",
    [string]$ProfilePath,
    [string]$BaseRoot = (Join-Path $env:LOCALAPPDATA "AdventureLabs\RevCalc"),
    [string]$ExistingRoot
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "RevCalc-Installation.ps1")
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw "Versão inválida." }
function Ensure-Python {
    try { & py -3.11 --version *> $null; if ($LASTEXITCODE -eq 0) { return } } catch {}
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw "Instale Python 3.11 com o launcher py e execute novamente." }
    & winget install --id Python.Python.3.11 -e --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) { throw "A instalação do Python falhou." }
    try { & py -3.11 --version *> $null } catch { throw "Reabra o PowerShell para usar o launcher py." }
    if ($LASTEXITCODE -ne 0) { throw "Reabra o PowerShell para usar o launcher py." }
}
Write-Host "RevCalc v$Version — instalação local" -ForegroundColor Cyan
Ensure-Python
if ($InstallLibreOffice -and -not (Get-Command soffice -ErrorAction SilentlyContinue)) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw "winget indisponível para instalar LibreOffice." }
    & winget install --id TheDocumentFoundation.LibreOffice -e --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) { throw "A instalação do LibreOffice falhou." }
}
# Unique temporary directory contains code only, never .env or tokens.
$tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$downloadRoot = Assert-RevCalcChildPath (Join-Path $tempRoot ("revcalc-download-" + [guid]::NewGuid().ToString("N"))) $tempRoot
New-Item -ItemType Directory -Path $downloadRoot | Out-Null
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $zipPath = Join-Path $downloadRoot "release.zip"
    Invoke-WebRequest -UseBasicParsing -Uri "https://github.com/adventurelabsbrasil/revcalc/archive/refs/tags/v$Version.zip" -OutFile $zipPath
    Expand-Archive -LiteralPath $zipPath -DestinationPath $downloadRoot
    $source = Join-Path $downloadRoot "revcalc-$Version"
    if (-not (Test-Path -LiteralPath (Join-Path $source "pyproject.toml"))) { throw "Pacote inválido." }
    Install-RevCalcRelease -SourceRoot $source -BaseRoot $BaseRoot -Version $Version -ProfilePath $ProfilePath -ExistingRoot $ExistingRoot | Out-Null
} finally {
    $checkedDownload = Assert-RevCalcChildPath $downloadRoot $tempRoot
    if (Test-Path -LiteralPath $checkedDownload) { Remove-Item -LiteralPath $checkedDownload -Recurse -Force }
}