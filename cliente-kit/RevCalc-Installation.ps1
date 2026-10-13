# Shared installation routines; importing this file does not install anything.
function Write-RevCalcUtf8 {
    param([string]$Path, [string]$Content)
    [IO.File]::WriteAllText($Path, $Content, (New-Object System.Text.UTF8Encoding($true)))
}

function Assert-RevCalcChildPath {
    param([string]$Path, [string]$Parent)
    $resolvedPath = [IO.Path]::GetFullPath($Path)
    $resolvedParent = [IO.Path]::GetFullPath($Parent).TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar
    if (-not $resolvedPath.StartsWith($resolvedParent, [StringComparison]::OrdinalIgnoreCase)) { throw "Caminho fora da pasta de instalação." }
    return $resolvedPath
}

function Invoke-RevCalcPython {
    param([string]$Executable, [string[]]$Arguments)
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Falha no Python/pip (código $LASTEXITCODE). Instalação anterior preservada." }
}

function Install-RevCalcRelease {
    param(
        [Parameter(Mandatory=$true)][string]$SourceRoot,
        [Parameter(Mandatory=$true)][string]$BaseRoot,
        [Parameter(Mandatory=$true)][string]$Version,
        [string]$ProfilePath,
        [string]$ExistingRoot,
        [string]$PythonCommand = "py",
        [string[]]$PythonPrefix = @("-3.11")
    )
    $ErrorActionPreference = "Stop"
    if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw "Versão inválida." }
    $SourceRoot = (Resolve-Path -LiteralPath $SourceRoot).Path
    if (-not (Test-Path -LiteralPath (Join-Path $SourceRoot "src\calculadora_crefaz\desktop_config.py"))) { throw "Pacote sem suporte ao perfil desktop. Use uma release atualizada." }
    $BaseRoot = [IO.Path]::GetFullPath($BaseRoot)
    New-Item -ItemType Directory -Force -Path $BaseRoot | Out-Null
    $activePath = Join-Path $BaseRoot "active.json"
    if (-not $ExistingRoot -and (Test-Path -LiteralPath $activePath)) {
        $active = Get-Content -LiteralPath $activePath -Raw -Encoding UTF8 | ConvertFrom-Json
        $ExistingRoot = Assert-RevCalcChildPath $active.install_root $BaseRoot
    }
    if (-not $ExistingRoot) {
        $legacyRoot = Join-Path $BaseRoot $Version
        if (Test-Path -LiteralPath $legacyRoot) { $ExistingRoot = $legacyRoot }
        else {
            $legacy = Get-ChildItem -LiteralPath $BaseRoot -Directory |
                Where-Object { $_.Name -match '^\d+\.\d+\.\d+$' -and (Test-Path -LiteralPath (Join-Path $_.FullName ".env")) } |
                Sort-Object { [version]$_.Name } -Descending | Select-Object -First 1
            if ($legacy) { $ExistingRoot = $legacy.FullName }
        }
    }
    $configRoot = Join-Path $BaseRoot "config"
    $persistentProfile = Join-Path $configRoot "revcalc-desktop.json"
    $persistentEnv = Join-Path $configRoot ".env"
    $selectedProfile = $null
    if (Test-Path -LiteralPath $persistentProfile) { $selectedProfile = $persistentProfile }
    elseif ($ProfilePath) { $selectedProfile = (Resolve-Path -LiteralPath $ProfilePath).Path }
    else {
        $kitProfile = Join-Path $PSScriptRoot "revcalc-desktop.json"
        if (Test-Path -LiteralPath $kitProfile) { $selectedProfile = $kitProfile }
    }
    $legacyEnv = $null
    if (Test-Path -LiteralPath $persistentEnv) { $legacyEnv = $persistentEnv }
    elseif ($ExistingRoot -and (Test-Path -LiteralPath (Join-Path $ExistingRoot ".env"))) { $legacyEnv = Join-Path $ExistingRoot ".env" }
    if (-not $selectedProfile -and -not $legacyEnv) { throw "Perfil desktop ausente. Use o kit configurado pela Adventure (revcalc-desktop.json). Não é necessário editar .env." }
    # Never move a venv/editable installation after pip has recorded its path.
    $candidate = Assert-RevCalcChildPath (Join-Path $BaseRoot ("versions\" + $Version + "-" + [guid]::NewGuid().ToString("N"))) $BaseRoot
    New-Item -ItemType Directory -Force -Path $candidate | Out-Null
    Get-ChildItem -LiteralPath $SourceRoot -Force |
        Where-Object { $_.Name -notin @(".git", ".venv", ".env", "revcalc-desktop.json") } |
        ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $candidate -Recurse -Force }
    if ($legacyEnv) { Copy-Item -LiteralPath $legacyEnv -Destination (Join-Path $candidate ".env") }
    $venv = Join-Path $candidate ".venv"
    Invoke-RevCalcPython $PythonCommand ($PythonPrefix + @("-m", "venv", $venv))
    $python = Join-Path $venv "Scripts\python.exe"
    Invoke-RevCalcPython $python @("-m", "pip", "install", "--upgrade", "pip")
    Invoke-RevCalcPython $python @("-m", "pip", "install", "-e", $candidate)
    $previousProfile = $env:REVCALC_PROFILE_PATH
    try {
        if ($selectedProfile) { $env:REVCALC_PROFILE_PATH = $selectedProfile }
        Invoke-RevCalcPython $python @("-m", "calculadora_crefaz.desktop_config")
        Invoke-RevCalcPython $python @("-c", "import calculadora_crefaz.auth; import calculadora_crefaz.drive; import calculadora_crefaz.ui")
    } finally { $env:REVCALC_PROFILE_PATH = $previousProfile }
    New-Item -ItemType Directory -Force -Path $configRoot | Out-Null
    if ($selectedProfile -and -not (Test-Path -LiteralPath $persistentProfile)) { Copy-Item -LiteralPath $selectedProfile -Destination $persistentProfile }
    if ($legacyEnv -and -not (Test-Path -LiteralPath $persistentEnv)) { Copy-Item -LiteralPath $legacyEnv -Destination $persistentEnv }
    $launcher = @'
$ErrorActionPreference = "Stop"
$active = Get-Content -LiteralPath (Join-Path $PSScriptRoot "active.json") -Raw -Encoding UTF8 | ConvertFrom-Json
$root = [IO.Path]::GetFullPath($active.install_root)
$base = [IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar
if (-not $root.StartsWith($base, [StringComparison]::OrdinalIgnoreCase)) { throw "Instalação ativa inválida." }
$profile = Join-Path $PSScriptRoot "config\revcalc-desktop.json"
if (Test-Path -LiteralPath $profile) { $env:REVCALC_PROFILE_PATH = $profile }
$legacyEnv = Join-Path $PSScriptRoot "config\.env"
if (Test-Path -LiteralPath $legacyEnv) { $env:REVCALC_ENV_PATH = $legacyEnv }
Set-Location -LiteralPath $root
& (Join-Path $root ".venv\Scripts\python.exe") -m calculadora_crefaz
if ($LASTEXITCODE -ne 0) { Read-Host "RevCalc encerrou com erro. Pressione Enter" }
'@
    Write-RevCalcUtf8 (Join-Path $BaseRoot "Executar-RevCalc.ps1") $launcher
    $activeTemp = Join-Path $BaseRoot ("active-" + [guid]::NewGuid().ToString("N") + ".json")
    Write-RevCalcUtf8 $activeTemp (@{version=$Version; install_root=$candidate} | ConvertTo-Json)
    if (Test-Path -LiteralPath $activePath) {
        [IO.File]::Replace($activeTemp, $activePath, (Join-Path $BaseRoot "previous-active.json"))
    } else { [IO.File]::Move($activeTemp, $activePath) }
    Write-Host "RevCalc pronto. Execute: $(Join-Path $BaseRoot 'Executar-RevCalc.ps1')" -ForegroundColor Green
    return $candidate
}
