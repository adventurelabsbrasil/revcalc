$ErrorActionPreference = "Stop"

$Version = "0.9.14"
$InstallRoot = Join-Path $env:LOCALAPPDATA "AdventureLabs\RevCalc\$Version"
$ZipPath = Join-Path $env:TEMP "revcalc-$Version.zip"
$ExtractRoot = Join-Path $env:TEMP "revcalc-$Version-extract"
$RepoZip = "https://github.com/adventurelabsbrasil/revcalc/archive/refs/tags/v$Version.zip"

function Require-Command([string]$Name, [string]$Hint) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) { throw "$Name não encontrado. $Hint" }
}

Write-Host "RevCalc v$Version — instalação local (sem servidor)" -ForegroundColor Cyan
Require-Command "py" "Instale Python 3.11+ e marque 'Add python.exe to PATH'."
if ($LASTEXITCODE -ne 0) { throw "Python 3.11 não encontrado." }

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
    @'
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
& .\.venv\Scripts\python.exe -m calculadora_crefaz
if ($LASTEXITCODE -ne 0) { Read-Host "RevCalc encerrou com erro. Pressione Enter" }
'@ | Set-Content -Path (Join-Path $InstallRoot "Executar-RevCalc.ps1") -Encoding UTF8
    Write-Host "Instalação concluída em: $InstallRoot" -ForegroundColor Green
    Write-Host "Edite .env e execute Executar-RevCalc.ps1."
} finally { Pop-Location }
