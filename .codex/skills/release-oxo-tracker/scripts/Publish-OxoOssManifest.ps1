param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version,
    [string]$WorkspaceRoot,
    [string]$OssDestination = "oss://oxotracker/stable/latest.json",
    [string]$PublicUrl = "https://oxotracker.oss-cn-beijing.aliyuncs.com/stable/latest.json",
    [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $WorkspaceRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\..\.."))
}
else { $WorkspaceRoot = [IO.Path]::GetFullPath($WorkspaceRoot) }
$releaseDirectory = Join-Path $WorkspaceRoot "artifacts\desktop-release\$Version"
$manifestPath = Join-Path $releaseDirectory "latest.json"
$installerName = "Oxo-Tracker_${Version}_x64-setup.exe"

& (Join-Path $PSScriptRoot "Test-OxoRelease.ps1") -Version $Version -WorkspaceRoot $WorkspaceRoot
if ($LASTEXITCODE -ne 0) { throw "Local release validation failed." }
$buildInfo = Get-Content -LiteralPath (Join-Path $releaseDirectory "BUILD-INFO.json") -Raw -Encoding UTF8 | ConvertFrom-Json
if (!$buildInfo.updater_signature_verified) { throw "Refusing OSS publication before independent updater signature verification." }
$localManifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$expectedInstallerUrl = "https://github.com/Oxo-AI-Security/Oxo-Tracker-Releases/releases/download/v$Version/$installerName"
if ($localManifest.version -ne $Version -or $localManifest.platforms.'windows-x86_64'.url -ne $expectedInstallerUrl) {
    throw "Local latest.json does not point to the expected GitHub release."
}

$release = Invoke-RestMethod -Uri "https://api.github.com/repos/Oxo-AI-Security/Oxo-Tracker-Releases/releases/tags/v$Version" -Headers @{ "User-Agent" = "Oxo-Release-Builder" } -TimeoutSec 60
if ($release.draft -or !$release.prerelease) { throw "GitHub v$Version is not a public Preview release." }
$remoteInstaller = @($release.assets | Where-Object name -eq $installerName)
if ($remoteInstaller.Count -ne 1 -or $remoteInstaller[0].state -ne "uploaded" -or [long]$remoteInstaller[0].size -ne (Get-Item -LiteralPath (Join-Path $releaseDirectory $installerName)).Length) {
    throw "The public GitHub installer is missing or differs in size from the validated local installer."
}

$ossutilCandidates = @(
    (Get-Command ossutil -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1),
    "D:\tools\ossutil\bin\ossutil.exe",
    "D:\tools\ossutil\ossutil-v2.3.0-windows-amd64\ossutil.exe"
) | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) }
$ossutil = $ossutilCandidates | Select-Object -First 1
if (!$ossutil) { throw "Configured ossutil was not found on PATH or under D:\tools\ossutil." }

if ($ValidateOnly) {
    [pscustomobject]@{
        status = "validated-only"
        version = $Version
        ossutil = $ossutil
        destination = $OssDestination
        public_url = $PublicUrl
        installer_url = $expectedInstallerUrl
    } | ConvertTo-Json
    return
}

& $ossutil cp $manifestPath $OssDestination --force --content-type "application/json; charset=utf-8" --cache-control "no-cache" --acl public-read --no-progress
if ($LASTEXITCODE -ne 0) { throw "ossutil failed to upload latest.json." }

$verifyRoot = Join-Path $WorkspaceRoot ".desktop-build\oss-verify"
New-Item -ItemType Directory -Path $verifyRoot -Force | Out-Null
$download = Join-Path $verifyRoot "latest-$Version-$([guid]::NewGuid().ToString('N')).json"
try {
    Invoke-WebRequest -Uri "$PublicUrl`?verify=$([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())" -OutFile $download -UseBasicParsing -TimeoutSec 60
    $localHash = (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $remoteHash = (Get-FileHash -LiteralPath $download -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($localHash -ne $remoteHash) { throw "Public OSS latest.json bytes do not match the local manifest." }
    $remoteManifest = Get-Content -LiteralPath $download -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($remoteManifest.version -ne $Version -or $remoteManifest.platforms.'windows-x86_64'.url -ne $expectedInstallerUrl) {
        throw "Public OSS latest.json semantic verification failed."
    }
    if ($remoteManifest.platforms.'windows-x86_64'.signature -ne $localManifest.platforms.'windows-x86_64'.signature) {
        throw "Public OSS updater signature differs from the validated local signature."
    }
    [pscustomobject]@{ version = $Version; oss_url = $PublicUrl; sha256 = $remoteHash; installer_url = $expectedInstallerUrl } | ConvertTo-Json
}
finally {
    if (Test-Path -LiteralPath $download -PathType Leaf) { Remove-Item -LiteralPath $download -Force }
}
