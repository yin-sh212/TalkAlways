[CmdletBinding()]
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
    [int]$Port = 3000
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "[backend] $Message"
}

$runlogsRoot = Join-Path $RepoRoot "runlogs"
$pidPath = Join-Path $runlogsRoot "backend.pid"
$stopped = $false

if (Test-Path $pidPath) {
    $pidValue = Get-Content $pidPath | Select-Object -First 1
    if ($pidValue) {
        $process = Get-Process -Id ([int]$pidValue) -ErrorAction SilentlyContinue
        if ($process) {
            Write-Step "Stopping backend process $pidValue"
            Stop-Process -Id ([int]$pidValue) -Force
            $stopped = $true
        }
    }
    Remove-Item $pidPath -Force
}

$listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
foreach ($listener in $listeners) {
    Write-Step "Stopping process $($listener.OwningProcess) on port $Port"
    Stop-Process -Id $listener.OwningProcess -Force -ErrorAction SilentlyContinue
    $stopped = $true
}

if (-not $stopped) {
    Write-Step "No backend process found on port $Port"
}
