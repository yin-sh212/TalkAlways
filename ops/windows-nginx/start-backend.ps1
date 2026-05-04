[CmdletBinding()]
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
    [string]$PythonExe = "python",
    [string]$BindHost = "0.0.0.0",
    [int]$Port = 3000,
    [int]$StartupTimeoutSec = 30,
    [switch]$SkipBackendDepsInstall,
    [switch]$UpgradePip
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "[backend] $Message"
}

function Resolve-PythonPath {
    param([string]$CommandValue)

    if (Test-Path $CommandValue) {
        return (Resolve-Path $CommandValue).Path
    }

    $command = Get-Command $CommandValue -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    throw "Python executable not found: $CommandValue"
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$Arguments = @(),
        [string]$FailureMessage = "Command failed"
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "${FailureMessage}. Exit code: $LASTEXITCODE"
    }
}

$serverRoot = Join-Path $RepoRoot "server"
$runlogsRoot = Join-Path $RepoRoot "runlogs"
$stdoutPath = Join-Path $runlogsRoot "backend.out.log"
$stderrPath = Join-Path $runlogsRoot "backend.err.log"
$pidPath = Join-Path $runlogsRoot "backend.pid"
$requirementsPath = Join-Path $serverRoot "requirements.txt"

if (-not (Test-Path $serverRoot)) {
    throw "Server directory not found: $serverRoot"
}

$existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    Write-Step "Backend already listening on port $Port"
    $existing | Select-Object LocalAddress, LocalPort, OwningProcess
    exit 0
}

New-Item -ItemType Directory -Force $runlogsRoot | Out-Null
if (Test-Path $stdoutPath) { Remove-Item $stdoutPath -Force }
if (Test-Path $stderrPath) { Remove-Item $stderrPath -Force }

$resolvedPython = Resolve-PythonPath $PythonExe

if (-not $SkipBackendDepsInstall) {
    if (-not (Test-Path $requirementsPath)) {
        throw "requirements.txt not found: $requirementsPath"
    }

    Push-Location $serverRoot
    try {
        if ($UpgradePip) {
            Write-Step "Upgrading pip"
            Invoke-Checked -FilePath $resolvedPython -Arguments @("-m", "pip", "install", "--upgrade", "pip") -FailureMessage "pip upgrade failed"
        }

        Write-Step "Installing backend dependencies"
        Invoke-Checked -FilePath $resolvedPython -Arguments @("-m", "pip", "install", "-r", "requirements.txt") -FailureMessage "Backend dependency install failed"
    }
    finally {
        Pop-Location
    }
}

$env:HOST = $BindHost
$env:PORT = "$Port"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

Write-Step "Starting backend with $resolvedPython"
$process = Start-Process `
    -FilePath $resolvedPython `
    -ArgumentList "start_server.py" `
    -WorkingDirectory $serverRoot `
    -RedirectStandardOutput $stdoutPath `
    -RedirectStandardError $stderrPath `
    -WindowStyle Hidden `
    -PassThru

Set-Content -Path $pidPath -Value $process.Id -Encoding Ascii

$deadline = (Get-Date).AddSeconds($StartupTimeoutSec)
while ((Get-Date) -lt $deadline) {
    if ($process.HasExited) {
        Write-Step "Backend process exited early with code $($process.ExitCode)"
        break
    }
    $listening = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($listening) {
        Write-Step "Backend is listening on ${BindHost}:${Port}"
        exit 0
    }
    Start-Sleep -Milliseconds 500
}

Write-Step "Backend failed to start within ${StartupTimeoutSec}s"
if (Test-Path $stdoutPath) {
    Write-Host "----- backend.out.log -----"
    Get-Content $stdoutPath
}
if (Test-Path $stderrPath) {
    Write-Host "----- backend.err.log -----"
    Get-Content $stderrPath
}
throw "Backend startup timed out"
