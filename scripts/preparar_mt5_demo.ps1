# Local deployment of signed MT5 binaries, without account/password databases.
$ErrorActionPreference = "Stop"
$source = "C:\Program Files\MetaTrader 5"
$destination = Join-Path $env:LOCALAPPDATA "TraderIANovo\MT5-Demo"
$signature = Get-AuthenticodeSignature -FilePath (Join-Path $source "terminal64.exe")
if ($signature.Status -ne "Valid" -or $signature.SignerCertificate.Subject -notmatch "MetaQuotes") {
    throw "Assinatura oficial do MT5 nao confirmada."
}
New-Item -ItemType Directory -Path $destination -Force | Out-Null
foreach ($name in @("terminal64.exe", "MetaEditor64.exe", "metatester64.exe", "Terminal.ico")) {
    $inputFile = Join-Path $source $name
    $outputFile = Join-Path $destination $name
    if (Test-Path -LiteralPath $outputFile) {
        if ((Get-FileHash -LiteralPath $inputFile).Hash -ne (Get-FileHash -LiteralPath $outputFile).Hash) {
            throw "Arquivo Demo existente diferente: $outputFile. Nada foi sobrescrito."
        }
    } else {
        Copy-Item -LiteralPath $inputFile -Destination $outputFile
    }
}
New-Item -ItemType Directory -Path (Join-Path $destination "Config") -Force | Out-Null
foreach ($name in @("servers.dat", "terminal.lic")) {
    $outputFile = Join-Path $destination "Config\$name"
    if (-not (Test-Path -LiteralPath $outputFile)) {
        Copy-Item -LiteralPath (Join-Path $source "Config\$name") -Destination $outputFile
    }
}
$shell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath("Desktop")
$demoLink = $shell.CreateShortcut((Join-Path $desktop "TraderIA Novo - MT5 DEMO.lnk"))
$demoLink.TargetPath = Join-Path $destination "terminal64.exe"
$demoLink.Arguments = "/portable"
$demoLink.WorkingDirectory = $destination
$demoLink.Description = "MT5 Demo separado - conta 61551556 - Pepperstone-Demo"
$demoLink.Save()
$realLink = $shell.CreateShortcut((Join-Path $desktop "TraderIA Novo - MT5 REAL.lnk"))
$realLink.TargetPath = Join-Path $source "terminal64.exe"
$realLink.WorkingDirectory = $source
$realLink.Description = "MT5 original reservado para Real - confirmar conta 51517136"
$realLink.Save()
Write-Output "Demo preparada em $destination. Nenhuma senha copiada; nenhuma ordem enviada."
