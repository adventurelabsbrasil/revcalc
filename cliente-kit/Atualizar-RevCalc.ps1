$ErrorActionPreference = "Stop"
$Repo = "adventurelabsbrasil/revcalc"
$InstallRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$CurrentVersion = "0.9.14"

$tags = Invoke-RestMethod -Headers @{ "User-Agent" = "AdventureLabs-RevCalc-Updater" } `
    -Uri "https://api.github.com/repos/$Repo/tags?per_page=30"
$latest = $tags.name | Where-Object { $_ -match '^v\d+\.\d+\.\d+$' } |
    Sort-Object { [version]($_.Substring(1)) } -Descending | Select-Object -First 1
if (-not $latest) { throw "Nenhuma versão encontrada no mirror." }
$LatestVersion = $latest.Substring(1)

Write-Host "Instalada: v$CurrentVersion | Disponível: v$LatestVersion"
if ([version]$LatestVersion -le [version]$CurrentVersion) { Write-Host "Já está atualizada."; exit 0 }
if ((Read-Host "Atualizar agora? (S/N)") -notmatch '^[sS]$') { exit 0 }

$temp = Join-Path $env:TEMP "revcalc-update-$LatestVersion"
$zip = Join-Path $env:TEMP "revcalc-$LatestVersion.zip"
if (Test-Path $temp) { Remove-Item $temp -Recurse -Force }
New-Item -ItemType Directory -Force -Path $temp | Out-Null
Invoke-WebRequest -Uri "https://github.com/$Repo/archive/refs/tags/v$LatestVersion.zip" -OutFile $zip
Expand-Archive -Path $zip -DestinationPath $temp -Force
$source = Join-Path $temp "revcalc-$LatestVersion"

$envFile = Join-Path $InstallRoot ".env"
$envBackup = Join-Path $env:TEMP "revcalc.env.backup"
if (Test-Path $envFile) { Copy-Item $envFile $envBackup -Force }
Get-ChildItem -LiteralPath $InstallRoot -Force |
    Where-Object { $_.Name -notin @(".env", ".venv", "Atualizar-RevCalc.ps1") } |
    Remove-Item -Recurse -Force
Copy-Item (Join-Path $source "*") $InstallRoot -Recurse -Force
if (Test-Path $envBackup) { Copy-Item $envBackup $envFile -Force }

Push-Location $InstallRoot
try {
    & .\.venv\Scripts\python.exe -m pip install --upgrade pip
    & .\.venv\Scripts\python.exe -m pip install -e "."
    Write-Host "Atualização concluída. .env preservado." -ForegroundColor Green
} finally { Pop-Location }
