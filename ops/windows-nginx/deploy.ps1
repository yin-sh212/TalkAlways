[CmdletBinding()]
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
    [string]$NginxRoot = "",
    [string]$BackendHost = "127.0.0.1",
    [int]$BackendPort = 3000,
    [string]$NodeRoot = "",
    [string]$NodeVersion = "20.19.5",
    [string]$NodeDownloadUrl = "",
    [string]$NginxVersion = "1.28.0",
    [string]$NginxDownloadUrl = "",
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

function Install-ArchiveIfMissing {
    param(
        [Parameter(Mandatory = $true)][string]$InstallRoot,
        [Parameter(Mandatory = $true)][string]$ExecutableRelativePath,
        [Parameter(Mandatory = $true)][string]$DefaultDownloadUrl,
        [string]$DownloadUrl,
        [Parameter(Mandatory = $true)][string]$ComponentName
    )

    $targetExecutable = Join-Path $InstallRoot $ExecutableRelativePath
    if (Test-Path $targetExecutable) {
        Write-Step "Using existing $ComponentName at $InstallRoot"
        return $targetExecutable
    }

    if (-not $DownloadUrl) {
        $DownloadUrl = $DefaultDownloadUrl
    }

    Write-Step "Downloading $ComponentName from $DownloadUrl"

    $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("talkalways-" + $ComponentName + "-" + [guid]::NewGuid().ToString("N"))
    $zipPath = Join-Path $tempRoot "$ComponentName.zip"
    $extractRoot = Join-Path $tempRoot "extract"

    New-Item -ItemType Directory -Force $tempRoot | Out-Null
    try {
        Invoke-WebRequest -Uri $DownloadUrl -OutFile $zipPath
        Expand-Archive -Path $zipPath -DestinationPath $extractRoot -Force

        $expandedDir = Get-ChildItem $extractRoot -Directory | Select-Object -First 1
        if (-not $expandedDir) {
            throw "Downloaded $ComponentName archive does not contain an extracted directory"
        }

        New-Item -ItemType Directory -Force $InstallRoot | Out-Null
        Copy-Item (Join-Path $expandedDir.FullName "*") $InstallRoot -Recurse -Force
    }
    finally {
        if (Test-Path $tempRoot) {
            Remove-Item -Recurse -Force $tempRoot
        }
    }

    if (-not (Test-Path $targetExecutable)) {
        throw "$ComponentName installation failed: $targetExecutable not found"
    }

    Write-Step "Installed $ComponentName to $InstallRoot"
    return $targetExecutable
}

function Resolve-NpmCommand {
    param(
        [string]$RepoRootPath,
        [string]$NodeInstallRoot,
        [string]$NodeVersionValue,
        [string]$NodeDownloadUrlValue,
        [bool]$NeedFrontendTooling
    )

    if (-not $NeedFrontendTooling) {
        return $null
    }

    $npmCommand = Get-Command npm -ErrorAction SilentlyContinue
    if ($npmCommand) {
        return $npmCommand.Source
    }

    if (-not $NodeInstallRoot) {
        $NodeInstallRoot = Join-Path $RepoRootPath "tools\nodejs"
    }

    $defaultNodeUrl = "https://nodejs.org/dist/v${NodeVersionValue}/node-v${NodeVersionValue}-win-x64.zip"
    $npmExecutable = Install-ArchiveIfMissing `
        -InstallRoot $NodeInstallRoot `
        -ExecutableRelativePath "npm.cmd" `
        -DefaultDownloadUrl $defaultNodeUrl `
        -DownloadUrl $NodeDownloadUrlValue `
        -ComponentName "nodejs"

    return $npmExecutable
}

function Invoke-NpmCommand {
    param(
        [Parameter(Mandatory = $true)][string]$NpmExecutable,
        [string[]]$Arguments = @(),
        [string]$FailureMessage = "npm command failed"
    )

    $nodeBinDir = Split-Path $NpmExecutable -Parent
    $originalPath = $env:PATH

    try {
        if ($nodeBinDir) {
            $env:PATH = "$nodeBinDir;$originalPath"
        }
        Invoke-Checked -FilePath $NpmExecutable -Arguments $Arguments -FailureMessage $FailureMessage
    }
    finally {
        $env:PATH = $originalPath
    }
}

function Invoke-Nginx {
    param(
        [Parameter(Mandatory = $true)][string]$ExecutablePath,
        [string[]]$Arguments = @(),
        [string]$FailureMessage = "nginx command failed"
    )

    Push-Location (Split-Path $ExecutablePath -Parent)
    try {
        Invoke-Checked -FilePath $ExecutablePath -Arguments $Arguments -FailureMessage $FailureMessage
    }
    finally {
        Pop-Location
    }
}

function Install-NginxIfMissing {
    param(
        [Parameter(Mandatory = $true)][string]$InstallRoot,
        [Parameter(Mandatory = $true)][string]$Version,
        [string]$DownloadUrl
    )

    if (-not $DownloadUrl) {
        $DownloadUrl = "https://nginx.org/download/nginx-$Version.zip"
    }

    [void](Install-ArchiveIfMissing `
        -InstallRoot $InstallRoot `
        -ExecutableRelativePath "nginx.exe" `
        -DefaultDownloadUrl $DownloadUrl `
        -DownloadUrl $DownloadUrl `
        -ComponentName "nginx")
}

function Get-LocalNginxMasterProcess {
    param([string]$InstallRoot)

    $pidFile = Join-Path $InstallRoot "logs\nginx.pid"
    if (-not (Test-Path $pidFile)) {
        return $null
    }

    $pidValue = Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $pidValue) {
        return $null
    }

    $pidValue = "$pidValue".Trim()
    if (-not $pidValue) {
        return $null
    }

    try {
        return Get-Process -Id ([int]$pidValue) -ErrorAction Stop
    }
    catch {
        return $null
    }
}

$clientRoot = Join-Path $RepoRoot "client"
$distRoot = Join-Path $clientRoot "dist"
$templatePath = Join-Path $PSScriptRoot "nginx.conf"

if (-not $NginxRoot) {
    $NginxRoot = Join-Path $RepoRoot "server\nginx"
}

$nginxExe = Join-Path $NginxRoot "nginx.exe"
$targetConfDir = Join-Path $NginxRoot "conf"
$targetConf = Join-Path $targetConfDir "nginx.conf"

if (-not (Test-Path $clientRoot)) {
    throw "Client directory not found: $clientRoot"
}

if (-not (Test-Path $templatePath)) {
    throw "Nginx template not found: $templatePath"
}

$needFrontendTooling = (-not $SkipFrontendBuild) -or $InstallFrontendDeps
$npmExecutable = Resolve-NpmCommand `
    -RepoRootPath $RepoRoot `
    -NodeInstallRoot $NodeRoot `
    -NodeVersionValue $NodeVersion `
    -NodeDownloadUrlValue $NodeDownloadUrl `
    -NeedFrontendTooling $needFrontendTooling

if (-not $SkipFrontendBuild) {
    Push-Location $clientRoot
    try {
        if ($InstallFrontendDeps) {
            Write-Step "Installing frontend dependencies"
            Invoke-NpmCommand -NpmExecutable $npmExecutable -Arguments @("install") -FailureMessage "npm install failed"
        }

        Write-Step "Building frontend"
        Invoke-NpmCommand -NpmExecutable $npmExecutable -Arguments @("run", "build") -FailureMessage "npm run build failed"
    }
    finally {
        Pop-Location
    }
}

if (-not (Test-Path $distRoot)) {
    throw "Frontend dist directory not found: $distRoot"
}

Install-NginxIfMissing -InstallRoot $NginxRoot -Version $NginxVersion -DownloadUrl $NginxDownloadUrl

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
Invoke-Nginx -ExecutablePath $nginxExe -Arguments @("-t") -FailureMessage "nginx config test failed"

$localNginx = Get-LocalNginxMasterProcess -InstallRoot $NginxRoot
if ($localNginx) {
    Write-Step "Reloading running nginx"
    Invoke-Nginx -ExecutablePath $nginxExe -Arguments @("-s", "reload") -FailureMessage "nginx reload failed"
}
elseif ($StartNginxIfStopped) {
    Write-Step "Starting nginx"
    Invoke-Nginx -ExecutablePath $nginxExe -FailureMessage "nginx start failed"
}
else {
    Write-Step "nginx is not running. Use -StartNginxIfStopped to start it."
}

Write-Step "Deployment script completed"
