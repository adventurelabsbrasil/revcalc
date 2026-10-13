param([string]$Scratch, [string]$ModulePath)
$ErrorActionPreference = "Stop"
. $ModulePath
function Assert-Equal {
    param($Actual, $Expected, [string]$Message)
    if ($Actual -ne $Expected) { throw $Message }
}
function Invoke-RevCalcPython {
    param([string]$Executable, [string[]]$Arguments)
    if ($script:FailInstall) { throw "Simulated pip failure" }
    # No process, keyring, network, or user's installation is touched.
}
$source = Join-Path $Scratch "source"
New-Item -ItemType Directory -Force -Path (Join-Path $source "src\calculadora_crefaz") | Out-Null
Write-RevCalcUtf8 (Join-Path $source "src\calculadora_crefaz\desktop_config.py") "# fixture"
Write-RevCalcUtf8 (Join-Path $source "pyproject.toml") 'version = "1.0.0"'
Write-RevCalcUtf8 (Join-Path $source "code.py") "new code"
$base = Join-Path $Scratch "installation with spaces"
$legacy = Join-Path $base "0.9.14"
New-Item -ItemType Directory -Force -Path $legacy | Out-Null
$legacyText = "GOOGLE_OAUTH_CLIENT_ID=legacy-test`nGOOGLE_OAUTH_CLIENT_SECRET=synthetic-test-secret`n"
Write-RevCalcUtf8 (Join-Path $legacy ".env") $legacyText
Write-RevCalcUtf8 (Join-Path $legacy "custom-config.txt") "preserve me"
$beforeEnv = [IO.File]::ReadAllBytes((Join-Path $legacy ".env"))
$first = Install-RevCalcRelease -SourceRoot $source -BaseRoot $base -Version "1.0.0"
$activePath = Join-Path $base "active.json"
$activeFirst = Get-Content -LiteralPath $activePath -Raw -Encoding UTF8 | ConvertFrom-Json
Assert-Equal $activeFirst.install_root $first "First activation failed"
Assert-Equal ([IO.File]::ReadAllText((Join-Path $first ".env"))) $legacyText "Legacy env changed"
Assert-Equal ([IO.File]::ReadAllText((Join-Path $legacy "custom-config.txt"))) "preserve me" "Custom config removed"
Assert-Equal ([Convert]::ToBase64String([IO.File]::ReadAllBytes((Join-Path $legacy ".env")))) ([Convert]::ToBase64String($beforeEnv)) "Legacy env bytes changed"
$pointerBeforeFailure = [IO.File]::ReadAllText($activePath)
$script:FailInstall = $true
try {
    Install-RevCalcRelease -SourceRoot $source -BaseRoot $base -Version "1.0.1" | Out-Null
    throw "Failure was not propagated"
} catch {
    if ($_.Exception.Message -ne "Simulated pip failure") { throw }
}
Assert-Equal ([IO.File]::ReadAllText($activePath)) $pointerBeforeFailure "Failed install changed active version"
$script:FailInstall = $false
$second = Install-RevCalcRelease -SourceRoot $source -BaseRoot $base -Version "1.0.0"
if ($first -eq $second) { throw "Reinstall reused the old installation directory" }
Assert-Equal (Test-Path -LiteralPath $first) $true "Reinstall destroyed previous version"
Assert-Equal ([IO.File]::ReadAllText((Join-Path $second ".env"))) $legacyText "Reinstall lost configuration"
$backup = Get-Content -LiteralPath (Join-Path $base "previous-active.json") -Raw -Encoding UTF8 | ConvertFrom-Json
Assert-Equal $backup.install_root $first "Rollback pointer incorrect"
$launcherBytes = [IO.File]::ReadAllBytes((Join-Path $base "Executar-RevCalc.ps1"))
Assert-Equal ([Convert]::ToBase64String($launcherBytes[0..2])) "77u/" "Launcher has no UTF8 BOM"
try {
    Assert-RevCalcChildPath (Join-Path $Scratch "outside") $base | Out-Null
    throw "Escaped path accepted"
} catch {
    if ($_.Exception.Message -ne "Caminho fora da pasta de instalação.") { throw }
}
$profileBase = Join-Path $Scratch "profile-only"
$profileFile = Join-Path $Scratch "managed-profile.json"
Write-RevCalcUtf8 $profileFile '{"schema_version":1,"client_type":"desktop","desktop_client_id":"123-test.apps.googleusercontent.com","allowed_domains":["client.example"],"drive_root_id":"TEST_ROOT","bacen_folder_id":"TEST_BACEN"}'
Install-RevCalcRelease -SourceRoot $source -BaseRoot $profileBase -Version "1.0.0" -ProfilePath $profileFile | Out-Null
$profileTarget = Join-Path $profileBase "config\revcalc-desktop.json"
$profileBefore = [IO.File]::ReadAllText($profileTarget)
Write-RevCalcUtf8 $profileFile '{"different":"ignored-on-reinstall"}'
Install-RevCalcRelease -SourceRoot $source -BaseRoot $profileBase -Version "1.0.0" -ProfilePath $profileFile | Out-Null
Assert-Equal ([IO.File]::ReadAllText($profileTarget)) $profileBefore "Existing profile overwritten"
Write-Host "PowerShell $($PSVersionTable.PSVersion): migration, reinstall, failure, rollback and profile preservation OK"
