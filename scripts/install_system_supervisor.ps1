param([switch]$Install)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $env:LOCALAPPDATA 'Python\pythoncore-3.14-64\pythonw.exe'
if (!(Test-Path -LiteralPath $python)) { throw 'Python sem console indisponivel' }
$runtime = Join-Path $root '.traderia\runtime'
$configPath = Join-Path $runtime 'supervisor_config.json'
if (!$Install) { Write-Output 'Use -Install para instalar checagem de minuto, auditoria horaria e vigilancia.'; exit }
New-Item -ItemType Directory -Path $runtime -Force | Out-Null
if (Test-Path -LiteralPath $configPath) {
    Copy-Item -LiteralPath $configPath -Destination ($configPath + '.before-' + (Get-Date -Format yyyyMMddHHmmss))
}
# Explicit previously authorized Demo identity; never adopt a connected account.
@{enabled=$true; login=61628148; server='Pepperstone-Demo'; terminal=(Join-Path $env:LOCALAPPDATA 'TraderIANovo\MT5-Demo\terminal64.exe'); mode='passive'; version=1} |
    ConvertTo-Json | Set-Content -LiteralPath $configPath -Encoding UTF8
$principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$settings.Priority = 7
foreach ($item in @(@{name='TraderIANovo Supervisor';minutes=1;arg=''},@{name='TraderIANovo Auditoria Horaria';minutes=60;arg='--daily'},@{name='TraderIANovo Supervisor Watch';minutes=5;arg='--watch'})) {
    $action = New-ScheduledTaskAction -Execute $python -Argument ('"'+(Join-Path $PSScriptRoot 'system_supervisor.py')+'" '+$item.arg) -WorkingDirectory $root
    $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes $item.minutes)
    $logon = New-ScheduledTaskTrigger -AtLogOn -User $principal.UserId
    if (Get-ScheduledTask -TaskName $item.name -ErrorAction SilentlyContinue) {
        Export-ScheduledTask -TaskName $item.name | Set-Content -LiteralPath (Join-Path $runtime ($item.name+'.before.xml'))
    }
    Register-ScheduledTask -TaskName $item.name -Action $action -Trigger @($trigger,$logon) -Settings $settings -Principal $principal -Force | Select-Object TaskName,State
}
