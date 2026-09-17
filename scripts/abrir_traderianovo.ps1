$ErrorActionPreference = "Stop"

$projectRoot = "C:\Users\evcab\OneDrive\Documentos\traderiaianovo"
$python = "C:\Users\evcab\AppData\Local\Python\pythoncore-3.14-64\python.exe"
$mt5Path = "C:\Program Files\MetaTrader 5\terminal64.exe"
$mt5DemoPath = Join-Path $env:LOCALAPPDATA "TraderIANovo\MT5-Demo\terminal64.exe"
$cloudflared = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
$cloudflareToken = "C:\Users\evcab\AppData\Local\TraderIANovo\cloudflared\tunnel-token.txt"
$cloudflareLogDirectory = Join-Path $projectRoot "logs"
$cloudflareOutputLog = Join-Path $cloudflareLogDirectory "cloudflared-traderianovo.out.log"
$cloudflareErrorLog = Join-Path $cloudflareLogDirectory "cloudflared-traderianovo.err.log"
$ramGuardScript = Join-Path $projectRoot "scripts\traderianovo_ram_guard.ps1"
$port = 8532
$url = "http://localhost:$port"
$publicUrl = "https://traderianovo.psiquiatriaemfoco.com"

function Test-TraderIAPort {
    return [bool](
        Get-NetTCPConnection `
            -LocalPort $port `
            -State Listen `
            -ErrorAction SilentlyContinue
    )
}

function Test-TraderIAHealth {
    if (-not (Test-TraderIAPort)) {
        return $false
    }
    try {
        $response = & curl.exe `
            --silent `
            --max-time 5 `
            "http://127.0.0.1:$port/_stcore/health" 2>$null
        return $LASTEXITCODE -eq 0 -and "$response".Trim().ToLowerInvariant() -eq "ok"
    }
    catch {
        return $false
    }
}

function Start-TraderIAMT5 {
    foreach ($path in @($mt5Path, $mt5DemoPath)) {
        $terminal = Get-CimInstance Win32_Process -Filter "Name='terminal64.exe'" `
            -ErrorAction SilentlyContinue | Where-Object { $_.ExecutablePath -eq $path }
        if ($terminal) {
            continue
        }
        if (-not (Test-Path -LiteralPath $path)) {
            Write-Warning "Terminal nao instalado: $path"
            continue
        }
        $startArguments = @{
            FilePath = $path
            WorkingDirectory = (Split-Path -Parent $path)
            WindowStyle = "Normal"
        }
        if ($path -eq $mt5DemoPath) {
            $startArguments.ArgumentList = @("/portable")
        }
        Start-Process @startArguments
        for ($attempt = 0; $attempt -lt 30; $attempt++) {
            $terminal = Get-CimInstance Win32_Process -Filter "Name='terminal64.exe'" `
                -ErrorAction SilentlyContinue | Where-Object { $_.ExecutablePath -eq $path }
            if ($terminal) {
                break
            }
            Start-Sleep -Seconds 1
        }
    }
}

function Get-TraderIACloudflaredProcesses {
    return @(
        Get-CimInstance Win32_Process -Filter "Name='cloudflared.exe'" `
            -ErrorAction SilentlyContinue |
        Where-Object {
            "$($_.CommandLine)" -like "*$cloudflareToken*"
        }
    )
}

function Test-TraderIAPublicHealth {
    try {
        $statusCode = & curl.exe `
            --silent `
            --output NUL `
            --write-out "%{http_code}" `
            --max-time 10 `
            $publicUrl 2>$null
        return $LASTEXITCODE -eq 0 -and "$statusCode" -match "^(200|301|302|307|308)$"
    }
    catch {
        return $false
    }
}

function Start-TraderIACloudflareTunnel {
    if (-not (Test-Path -LiteralPath $cloudflared)) {
        return
    }
    if (-not (Test-Path -LiteralPath $cloudflareToken)) {
        return
    }
    $tunnelProcesses = @(Get-TraderIACloudflaredProcesses)
    if ($tunnelProcesses.Count -gt 0) {
        if (Test-TraderIAPublicHealth) {
            return
        }
        foreach ($tunnelProcess in $tunnelProcesses) {
            Stop-Process `
                -Id $tunnelProcess.ProcessId `
                -Force `
                -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 2
    }

    New-Item -ItemType Directory -Path $cloudflareLogDirectory -Force | Out-Null
    Start-Process `
        -FilePath $cloudflared `
        -ArgumentList @(
            "tunnel",
            "run",
            "--token-file",
            "`"$cloudflareToken`""
        ) `
        -WorkingDirectory $projectRoot `
        -RedirectStandardOutput $cloudflareOutputLog `
        -RedirectStandardError $cloudflareErrorLog `
        -WindowStyle Hidden
}

function Start-TraderIARamGuard {
    if (-not (Test-Path -LiteralPath $ramGuardScript)) {
        return
    }
    $guardProcesses = @(
        Get-CimInstance Win32_Process `
            -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -in @("powershell.exe", "pwsh.exe") -and
            "$($_.CommandLine)" -like "*$ramGuardScript*"
        }
    )
    if ($guardProcesses.Count -gt 0) {
        return
    }
    Start-Process `
        -FilePath "powershell.exe" `
        -ArgumentList @(
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "`"$ramGuardScript`"",
            "-Port",
            "$port",
            "-MemoryLimitMB",
            "1600"
        ) `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden
}

if ((Test-TraderIAPort) -and -not (Test-TraderIAHealth)) {
    $staleProcesses = @(
        Get-NetTCPConnection `
            -LocalPort $port `
            -State Listen `
            -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
    )
    foreach ($processId in $staleProcesses) {
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

Start-TraderIAMT5

if (-not (Test-TraderIAHealth)) {
    $env:TRADERIA_EXECUTION_ACCOUNT_MODE = "DEMO"
    $env:TRADERIA_REAL_EXECUTION_ENABLED = "0"
    $env:TRADERIA_DEMO_ACCOUNT_LOGIN = "61551556"
    $env:TRADERIA_DEMO_ACCOUNT_SERVER = "Pepperstone-Demo"
    $env:TRADERIA_DEMO_EXECUTION_ENABLED = "1"
    $env:TRADERIA_MT5_INPROCESS_ENABLED = "1"
    $env:TRADERIA_MT5_MARKET_DATA_EXTERNAL_PROCESS_ENABLED = "1"
    $env:TRADERIA_MT5_WARM_CACHE_ENABLED = "1"
    $env:TRADERIA_MT5_REPORT_EXTERNAL_PROCESS_ENABLED = "1"
    $env:TRADERIA_MT5_EXECUTION_READ_EXTERNAL_PROCESS_ENABLED = "1"
    $env:TRADERIA_MT5_RUNTIME_TTL_SECONDS = "10"
    $env:TRADERIA_MT5_RUNTIME_CACHE_SECONDS = "10"
    $env:TRADERIA_MT5_SERVER_TIME_CACHE_SECONDS = "10"
    $env:TRADERIA_MT5_REPORT_EXTERNAL_TIMEOUT_SECONDS = "8"
    $env:MT5_PATH = $mt5DemoPath
    $env:MT5_PORTABLE = "1"

    $arguments = @(
        "-m",
        "streamlit",
        "run",
        "dashboard_app.py",
        "--server.port",
        "$port",
        "--server.address",
        "127.0.0.1",
        "--server.headless",
        "true",
        "--server.fileWatcherType",
        "none",
        "--browser.gatherUsageStats",
        "false"
    )

    Start-Process `
        -FilePath $python `
        -ArgumentList $arguments `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden

    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        if (Test-TraderIAHealth) {
            break
        }
        Start-Sleep -Seconds 1
    }
}

if (Test-TraderIAHealth) {
    Start-Process -FilePath $python `
        -ArgumentList @("`"$(Join-Path $projectRoot 'scripts\run_additional_real.py')`"") `
        -WorkingDirectory $projectRoot -WindowStyle Hidden
    Start-TraderIARamGuard
    Start-TraderIACloudflareTunnel
    Start-Process $url
    exit 0
}

Add-Type -AssemblyName PresentationFramework
[System.Windows.MessageBox]::Show(
    "O TraderIA Novo nao conseguiu iniciar na porta 8532.",
    "TraderIA Novo",
    "OK",
    "Error"
) | Out-Null
exit 1
