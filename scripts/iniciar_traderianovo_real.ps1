# Manual entry point. Never run this from a scheduler or another launcher.
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$expectedRoot = "C:\Users\evcab\OneDrive\Documentos\traderiaianovo"
if ([IO.Path]::GetFullPath($projectRoot) -ne [IO.Path]::GetFullPath($expectedRoot)) {
    throw "Este inicializador pertence exclusivamente ao TraderIA Novo."
}

$listener = Get-NetTCPConnection -LocalPort 8532 -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    throw "Existe um painel na porta 8532. Desarme o robo e encerre esse painel antes de iniciar em Real. Nenhum processo foi alterado."
}

Write-Host "TraderIA Novo - conta REAL 51517136 / PepperstoneBS-MT5-Live01"
Write-Host "Os setups e lotes atuais serao mantidos. Saldo sera consultado no MT5."
Write-Host "Sem limite diario adicional. Stops das entradas permanecem ativos."
Write-Host "ATENCAO: a agenda e o estado armado salvos podem iniciar negociacoes automaticamente."
$confirmation = Read-Host "Para habilitar negociacao com dinheiro real, digite REAL 51517136"
if ($confirmation -cne "REAL 51517136") {
    Write-Host "Cancelado. Nenhuma configuracao operacional foi alterada."
    return
}

$env:TRADERIA_EXECUTION_ACCOUNT_MODE = "REAL"
$env:TRADERIA_REAL_EXECUTION_ENABLED = "1"
$env:TRADERIA_REAL_ACCOUNT_LOGIN = "51517136"
$env:TRADERIA_REAL_ACCOUNT_SERVER = "PepperstoneBS-MT5-Live01"
$env:TRADERIA_DEMO_MAX_DAILY_LOSS = "0"
Set-Location -LiteralPath $projectRoot
& (Join-Path $PSScriptRoot "abrir_traderianovo.ps1")
