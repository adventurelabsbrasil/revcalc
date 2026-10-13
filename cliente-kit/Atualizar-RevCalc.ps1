param([string]$BaseRoot = (Join-Path $env:LOCALAPPDATA "AdventureLabs\RevCalc"))
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "RevCalc-Installation.ps1")
$repo = "adventurelabsbrasil/revcalc"
$installedRoot = Split-Path -Parent $PSScriptRoot
$currentVersion = "0.9.15"
$activePath = Join-Path $BaseRoot "active.json"
if (Test-Path -LiteralPath $activePath) {
    $active = Get-Content -LiteralPath $activePath -Raw -Encoding UTF8 | ConvertFrom-Json
    $installedRoot = Assert-RevCalcChildPath $active.install_root $BaseRoot
    $currentVersion = $active.version
} else {
    $project = Join-Path $installedRoot "pyproject.toml"
    if (Test-Path -LiteralPath $project) {
        $line = Get-Content -LiteralPath $project -Encoding UTF8 | Where-Object { $_ -match '^version\s*=\s*"(\d+\.\d+\.\d+)"' } | Select-Object -First 1
        if ($line -match '"(\d+\.\d+\.\d+)"') { $currentVersion = $Matches[1] }
    }
}
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$tags = Invoke-RestMethod -Headers @{"User-Agent"="AdventureLabs-RevCalc-Updater"} -Uri "https://api.github.com/repos/$repo/tags?per_page=100"
$latest = $tags.name | Where-Object { $_ -match '^v\d+\.\d+\.\d+$' } |
    Sort-Object { [version]($_.Substring(1)) } -Descending | Select-Object -First 1
if (-not $latest) { throw "Nenhuma versão encontrada." }
$latestVersion = $latest.Substring(1)
Write-Host "Instalada: v$currentVersion | Disponível: v$latestVersion"
if ([version]$latestVersion -le [version]$currentVersion) { Write-Host "Já está atualizada."; exit 0 }
if ((Read-Host "Atualizar agora? (S/N)") -notmatch '^[sS]$') { exit 0 }
& (Join-Path $PSScriptRoot "Install-RevCalc.ps1") -Version $latestVersion -BaseRoot $BaseRoot -ExistingRoot $installedRoot