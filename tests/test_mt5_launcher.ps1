$ErrorActionPreference = "Stop"
$launcher = Join-Path (Split-Path -Parent $PSScriptRoot) "scripts\abrir_traderianovo.ps1"
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($launcher, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw "Erro de sintaxe no inicializador." }
$definition = $ast.Find({ param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Start-TraderIAMT5'
}, $true)
. ([scriptblock]::Create($definition.Extent.Text))

$mt5Path = 'C:\test\real\terminal64.exe'
$mt5DemoPath = 'C:\test\demo\terminal64.exe'
function Get-CimInstance { param($ClassName, $Filter, $ErrorAction) return $script:running }
function Test-Path { param($LiteralPath) return $true }
function Start-Process {
    param($FilePath, $WorkingDirectory, $WindowStyle, $ArgumentList)
    $script:started += [pscustomobject]@{ Path=$FilePath; Arguments=$ArgumentList }
    $script:running += [pscustomobject]@{ ExecutablePath=$FilePath }
}
function Start-Sleep { param($Seconds) throw "A espera nao deveria ser necessaria no teste." }

foreach ($case in @(
    @{ Existing=@(); Expected=@($mt5Path,$mt5DemoPath) },
    @{ Existing=@($mt5Path); Expected=@($mt5DemoPath) },
    @{ Existing=@($mt5DemoPath); Expected=@($mt5Path) },
    @{ Existing=@($mt5Path,$mt5DemoPath); Expected=@() }
)) {
    $script:running = @($case.Existing | ForEach-Object { [pscustomobject]@{ ExecutablePath=$_ } })
    $script:started = @()
    Start-TraderIAMT5
    if (($script:started.Path -join '|') -ne ($case.Expected -join '|')) { throw "Instancias iniciadas divergentes." }
    foreach ($start in $script:started) {
        if ($start.Path -eq $mt5DemoPath -and $start.Arguments -notcontains '/portable') { throw "Demo sem isolamento portable." }
        if ($start.Path -eq $mt5Path -and $start.Arguments) { throw "Argumentos inesperados no terminal original." }
    }
}
Write-Output '4 cenarios passaram. Nenhum terminal ou robo foi iniciado pelos testes.'
