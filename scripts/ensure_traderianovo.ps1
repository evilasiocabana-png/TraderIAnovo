# Scheduled recovery. Does not change trading selection or arm/disarm state.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$healthy = $false
try {
    $response = Invoke-WebRequest 'http://127.0.0.1:8532/_stcore/health' -UseBasicParsing -TimeoutSec 10
    $healthy = $response.StatusCode -eq 200 -and $response.Content.Trim() -eq 'ok'
} catch { }
$guardPath = Join-Path $PSScriptRoot 'traderianovo_ram_guard.ps1'
$guard = Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object {
    $_.CommandLine -match ('-File\s+"?' + [regex]::Escape($guardPath) + '"?(?:\s|$)')
}
$demoPath = Join-Path $env:LOCALAPPDATA 'TraderIANovo\MT5-Demo\terminal64.exe'
$terminal = Get-CimInstance Win32_Process -Filter "Name='terminal64.exe'" | Where-Object { $_.ExecutablePath -eq $demoPath }
if ($healthy -and $guard -and $terminal) {
    & "$env:LOCALAPPDATA/Python/pythoncore-3.14-64/python.exe" (Join-Path $PSScriptRoot 'ensure_runtime_started.py')
    exit $LASTEXITCODE
}
Set-Location -LiteralPath $root
& (Join-Path $PSScriptRoot 'abrir_traderianovo.ps1') -NoBrowser
exit $LASTEXITCODE
