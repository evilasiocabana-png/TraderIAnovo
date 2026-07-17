param(
    [int]$Port = 8532,
    [int]$MemoryLimitMB = 3500,
    [int]$CheckIntervalSeconds = 30,
    [switch]$Once
)

$ErrorActionPreference = "Continue"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$DashboardPath = Join-Path $ProjectRoot "dashboard_app.py"
$RuntimeDir = Join-Path $ProjectRoot ".traderia\runtime"
$LogPath = Join-Path $RuntimeDir "streamlit_ram_guard.jsonl"

function Write-GuardLog {
    param(
        [string]$Event,
        [object]$Payload
    )
    New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
    $record = [ordered]@{
        timestamp = (Get-Date).ToString("o")
        event = $Event
        payload = $Payload
    }
    ($record | ConvertTo-Json -Compress -Depth 6) | Add-Content -Path $LogPath -Encoding UTF8
}

function Get-TraderIAStreamlitProcess {
    $listeningOwners = @()
    try {
        $listeningOwners = @(
            Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
                Select-Object -ExpandProperty OwningProcess -Unique
        )
    } catch {
        $listeningOwners = @()
    }
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.CommandLine -match "streamlit" -and
            $_.CommandLine -match "dashboard_app.py" -and
            $_.CommandLine -match "--server.port $Port|--server.port=$Port|localhost:$Port|:$Port" -and
            ($listeningOwners.Count -eq 0 -or $listeningOwners -contains $_.ProcessId)
        } |
        ForEach-Object {
            $process = Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue
            if ($null -ne $process) {
                [PSCustomObject]@{
                    ProcessId = $_.ProcessId
                    Name = $_.Name
                    CommandLine = $_.CommandLine
                    WorkingSetMB = [math]::Round($process.WorkingSet64 / 1MB, 2)
                }
            }
        }
}

function Start-TraderIAStreamlit {
    $python = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $python) {
        Write-GuardLog -Event "start_failed" -Payload @{ reason = "python_not_found" }
        return
    }
    $script = @"
`$env:TRADERIA_DEMO_EXECUTION_ENABLED='1'
`$env:TRADERIA_MT5_INPROCESS_ENABLED='1'
Set-Location '$ProjectRoot'
& '$python' -m streamlit run '$DashboardPath' --server.port $Port --server.headless true
"@
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($script))
    Start-Process -FilePath "powershell.exe" -WindowStyle Hidden -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-EncodedCommand",
        $encoded
    ) | Out-Null
    Write-GuardLog -Event "started" -Payload @{ port = $Port; memory_limit_mb = $MemoryLimitMB }
}

function Invoke-GuardCycle {
    $processes = @(Get-TraderIAStreamlitProcess)
    if ($processes.Count -eq 0) {
        Write-GuardLog -Event "not_running" -Payload @{ port = $Port }
        Start-TraderIAStreamlit
        return
    }
    foreach ($proc in $processes) {
        if ([double]$proc.WorkingSetMB -ge $MemoryLimitMB) {
            Write-GuardLog -Event "memory_limit_reached" -Payload $proc
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 3
            Start-TraderIAStreamlit
        } else {
            Write-GuardLog -Event "healthy" -Payload $proc
        }
    }
}

do {
    Invoke-GuardCycle
    if ($Once) {
        break
    }
    Start-Sleep -Seconds $CheckIntervalSeconds
} while ($true)
