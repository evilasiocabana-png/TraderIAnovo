param(
    [int]$Port = 8532,
    [int]$MemoryLimitMB = 1600,
    [int]$CheckIntervalSeconds = 60,
    [int]$HealthyLogIntervalSeconds = 600,
    [int]$HealthFailureThreshold = 3,
    [switch]$Once
)

$ErrorActionPreference = "Continue"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$DashboardPath = Join-Path $ProjectRoot "dashboard_app.py"
$RuntimeDir = Join-Path $ProjectRoot ".traderia\runtime"
$LogPath = Join-Path $RuntimeDir "streamlit_ram_guard.jsonl"
$LastHealthyLogAt = [datetime]::MinValue
$ConsecutiveHealthFailures = 0
$TrackedProcessId = 0
$Mutex = New-Object System.Threading.Mutex(
    $false,
    "Local\TraderIANovoRamGuard_$Port"
)
if (-not $Mutex.WaitOne(0)) {
    exit 0
}

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
    try {
        ($record | ConvertTo-Json -Compress -Depth 6) |
            Add-Content -Path $LogPath -Encoding UTF8 -ErrorAction Stop
    } catch {
        return
    }
}

function Get-TraderIAStreamlitProcess {
    if ($script:TrackedProcessId -gt 0) {
        $tracked = Get-Process -Id $script:TrackedProcessId -ErrorAction SilentlyContinue
        if ($null -ne $tracked) {
            return [PSCustomObject]@{
                ProcessId = $script:TrackedProcessId
                Name = $tracked.ProcessName
                WorkingSetMB = [math]::Round($tracked.WorkingSet64 / 1MB, 2)
            }
        }
        $script:TrackedProcessId = 0
    }
    $listeningOwners = @(
        netstat -ano -p tcp |
            Select-String -Pattern ":$Port\s+.*LISTENING\s+(\d+)\s*$" |
            ForEach-Object { [int]$_.Matches[0].Groups[1].Value } |
            Select-Object -Unique
    )
    foreach ($processId in $listeningOwners) {
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($null -ne $process) {
            $script:TrackedProcessId = $processId
            [PSCustomObject]@{
                ProcessId = $processId
                Name = $process.ProcessName
                WorkingSetMB = [math]::Round($process.WorkingSet64 / 1MB, 2)
            }
            break
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
`$env:MT5_PATH='C:\Program Files\MetaTrader 5\terminal64.exe'
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

function Test-TraderIAStreamlitHealth {
    try {
        $response = Invoke-WebRequest `
            -Uri "http://127.0.0.1:$Port/_stcore/health" `
            -UseBasicParsing `
            -TimeoutSec 5 `
            -ErrorAction Stop
        return [int]$response.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Invoke-GuardCycle {
    $processes = @(Get-TraderIAStreamlitProcess)
    if ($processes.Count -eq 0) {
        Write-GuardLog -Event "not_running" -Payload @{ port = $Port }
        Start-TraderIAStreamlit
        return
    }
    if (-not (Test-TraderIAStreamlitHealth)) {
        $script:ConsecutiveHealthFailures += 1
        Write-GuardLog -Event "health_check_pending" -Payload @{
            port = $Port
            process_ids = @($processes | Select-Object -ExpandProperty ProcessId)
            consecutive_failures = $script:ConsecutiveHealthFailures
            threshold = $HealthFailureThreshold
        }
        if ($script:ConsecutiveHealthFailures -lt $HealthFailureThreshold) {
            return
        }
        foreach ($proc in $processes) {
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
        }
        $script:TrackedProcessId = 0
        $script:ConsecutiveHealthFailures = 0
        Start-Sleep -Seconds 3
        Start-TraderIAStreamlit
        return
    }
    $script:ConsecutiveHealthFailures = 0
    foreach ($proc in $processes) {
        if ([double]$proc.WorkingSetMB -ge $MemoryLimitMB) {
            Write-GuardLog -Event "memory_limit_reached" -Payload $proc
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
            $script:TrackedProcessId = 0
            Start-Sleep -Seconds 3
            Start-TraderIAStreamlit
        } else {
            $now = Get-Date
            if (($now - $script:LastHealthyLogAt).TotalSeconds -ge $HealthyLogIntervalSeconds) {
                Write-GuardLog -Event "healthy" -Payload $proc
                $script:LastHealthyLogAt = $now
            }
        }
    }
}

try {
    do {
        Invoke-GuardCycle
        if ($Once) {
            break
        }
        Start-Sleep -Seconds $CheckIntervalSeconds
    } while ($true)
} finally {
    $Mutex.ReleaseMutex()
    $Mutex.Dispose()
}
