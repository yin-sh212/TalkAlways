[CmdletBinding()]
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
    [string]$NginxRoot = "C:\nginx",
    [string]$BackendHost = "127.0.0.1",
    [int]$BackendPort = 3000,
    [switch]$InstallFrontendDeps,
    [switch]$SkipFrontendBuild,
    [switch]$SkipNginxControl,
    [switch]$StartNginxIfStopped
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "[deploy] $Message"
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

function Convert-ToNginxPath {
    param([string]$PathValue)
    return ($PathValue -replace "\\", "/")
}

$clientRoot = Join-Path $RepoRoot "client"
$distRoot = Join-Path $clientRoot "dist"
$templatePath = Join-Path $PSScriptRoot "nginx.conf"
$nginxExe = Join-Path $NginxRoot "nginx.exe"
$targetConfDir = Join-Path $NginxRoot "conf"
$targetConf = Join-Path $targetConfDir "nginx.conf"

if (-not (Test-Path $clientRoot)) {
    throw "Client directory not found: $clientRoot"
}

if (-not (Test-Path $templatePath)) {
    throw "Nginx template not found: $templatePath"
}

$npmCommand = Get-Command npm -ErrorAction SilentlyContinue
if ((-not $SkipFrontendBuild -or $InstallFrontendDeps) -and -not $npmCommand) {
    throw "npm command not found in PATH"
}

if (-not $SkipFrontendBuild) {
    Push-Location $clientRoot
    try {
        if ($InstallFrontendDeps) {
            Write-Step "Installing frontend dependencies"
            Invoke-Checked -FilePath $npmCommand.Source -Arguments @("install") -FailureMessage "npm install failed"
        }

        Write-Step "Building frontend"
        Invoke-Checked -FilePath $npmCommand.Source -Arguments @("run", "build") -FailureMessage "npm run build failed"
    }
    finally {
        Pop-Location
    }
}

if (-not (Test-Path $distRoot)) {
    throw "Frontend dist directory not found: $distRoot"
}

Write-Step "Rendering nginx.conf"
$distRootForNginx = Convert-ToNginxPath ((Resolve-Path $distRoot).Path)
$backendProxy = "http://${BackendHost}:${BackendPort}"
$confContent = Get-Content $templatePath -Raw
$confContent = [regex]::Replace(
    $confContent,
    "root\s+[^;]+;",
    "root   ${distRootForNginx};",
    [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
)
$confContent = $confContent -replace "http://127\.0\.0\.1:3000", $backendProxy

New-Item -ItemType Directory -Force $targetConfDir | Out-Null

if (Test-Path $targetConf) {
    $backupPath = "$targetConf.bak.$(Get-Date -Format 'yyyyMMddHHmmss')"
    Copy-Item $targetConf $backupPath -Force
    Write-Step "Backed up existing nginx.conf to $backupPath"
}

Set-Content -Path $targetConf -Value $confContent -Encoding Ascii
Write-Step "Wrote nginx config to $targetConf"

if ($SkipNginxControl) {
    Write-Step "SkipNginxControl enabled; config generation finished"
    exit 0
}

if (-not (Test-Path $nginxExe)) {
    throw "nginx.exe not found: $nginxExe"
}

Write-Step "Testing nginx configuration"
Invoke-Checked -FilePath $nginxExe -Arguments @("-t") -FailureMessage "nginx config test failed"

$nginxProcess = Get-Process -Name nginx -ErrorAction SilentlyContinue
if ($nginxProcess) {
    Write-Step "Reloading running nginx"
    Invoke-Checked -FilePath $nginxExe -Arguments @("-s", "reload") -FailureMessage "nginx reload failed"
}
elseif ($StartNginxIfStopped) {
    Write-Step "Starting nginx"
    Invoke-Checked -FilePath $nginxExe -FailureMessage "nginx start failed"
}
else {
    Write-Step "nginx is not running. Use -StartNginxIfStopped to start it."
}

Write-Step "Deployment script completed"
