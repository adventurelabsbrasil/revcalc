param([switch]$InstallLibreOffice)

$ErrorActionPreference = "Stop"

$Version = "0.9.14"
$InstallRoot = Join-Path $env:LOCALAPPDATA "AdventureLabs\RevCalc\$Version"
$ZipPath = Join-Path $env:TEMP "revcalc-$Version.zip"
$ExtractRoot = Join-Path $env:TEMP "revcalc-$Version-extract"
$RepoZip = "https://github.com/adventurelabsbrasil/revcalc/archive/refs/tags/v$Version.zip"

function Ensure-Python {
    $ok = $false
    try { & py -3.11 --version *> $null; $ok = ($LASTEXITCODE -eq 0) } catch { $ok = $false }
    if ($ok) { return }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "Python 3.11+ não encontrado e winget não está disponível. Instale Python manualmente."
    }
    Write-Host "Python 3.11 não encontrado. Instalando via winget..."
    & winget install --id Python.Python.3.11 -e --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) { throw "A instalação do Python falhou." }
    try { & py -3.11 --version *> $null } catch { throw "Python foi instalado, mas o launcher py não está disponível. Feche e abra o PowerShell e execute novamente." }
    if ($LASTEXITCODE -ne 0) { throw "Python foi instalado, mas o launcher py não está disponível. Feche e abra o PowerShell e execute novamente." }
}

function Ensure-LibreOffice {
    if (Get-Command soffice -ErrorAction SilentlyContinue) { return }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw "winget não disponível para instalar o LibreOffice." }
    & winget install --id TheDocumentFoundation.LibreOffice -e --accept-source-agreements --accept-package-agreements
}

Write-Host "RevCalc v$Version — instalação local (sem servidor)" -ForegroundColor Cyan
Ensure-Python
if ($InstallLibreOffice) { Ensure-LibreOffice }

if (Test-Path $ExtractRoot) { Remove-Item $ExtractRoot -Recurse -Force }
New-Item -ItemType Directory -Force -Path $ExtractRoot | Out-Null
Invoke-WebRequest -Uri $RepoZip -OutFile $ZipPath
Expand-Archive -Path $ZipPath -DestinationPath $ExtractRoot -Force

$SourceRoot = Join-Path $ExtractRoot "revcalc-$Version"
if (-not (Test-Path (Join-Path $SourceRoot "pyproject.toml"))) { throw "Download inválido." }
if (Test-Path $InstallRoot) { Remove-Item $InstallRoot -Recurse -Force }
New-Item -ItemType Directory -Force -Path (Split-Path $InstallRoot) | Out-Null
Move-Item -Path $SourceRoot -Destination $InstallRoot

Push-Location $InstallRoot
try {
    & py -3.11 -m venv .venv
    & .\.venv\Scripts\python.exe -m pip install --upgrade pip
    & .\.venv\Scripts\python.exe -m pip install -e "."
    if (-not (Test-Path ".env")) {
        Copy-Item ".env.example" ".env"
        Write-Warning "Preencha .env com as credenciais Google antes da primeira execução."
    }
    $Launcher = @(
        '$ErrorActionPreference = "Stop"'
        'Set-Location $PSScriptRoot'
        '& .\.venv\Scripts\python.exe -m calculadora_crefaz'
        'if ($LASTEXITCODE -ne 0) { Read-Host "RevCalc encerrou com erro. Pressione Enter" }'
    ) -join [Environment]::NewLine
    $Launcher | Set-Content -Path (Join-Path $InstallRoot "Executar-RevCalc.ps1") -Encoding UTF8
    Write-Host "Instalação concluída em: $InstallRoot" -ForegroundColor Green
    Write-Host "Edite .env e execute Executar-RevCalc.ps1."
} finally { Pop-Location }
