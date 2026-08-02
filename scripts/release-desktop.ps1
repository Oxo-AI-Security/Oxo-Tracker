param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$')]
    [string]$Version,
    [string]$CertificateThumbprint = $env:OXO_SIGNING_CERT_THUMBPRINT,
    [string]$TimestampUrl = "http://timestamp.digicert.com",
    [string]$UpdaterPublicKey = $env:OXO_UPDATER_PUBLIC_KEY,
    [string]$UpdaterEndpoint = "https://oxotracker.oss-cn-beijing.aliyuncs.com/stable/latest.json",
    [switch]$SkipTests,
    [switch]$AllowDirty
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = [IO.Path]::GetFullPath((Split-Path $PSScriptRoot -Parent))
$defaultUpdaterPublicKeyPath = Join-Path $WorkspaceRoot "frontend\src-tauri\updater.pubkey"
if ([string]::IsNullOrWhiteSpace($UpdaterPublicKey) -and (Test-Path -LiteralPath $defaultUpdaterPublicKeyPath -PathType Leaf)) {
    $UpdaterPublicKey = $defaultUpdaterPublicKeyPath
}

if (!$CertificateThumbprint) {
    throw "Set OXO_SIGNING_CERT_THUMBPRINT or pass -CertificateThumbprint for a formal release."
}
if (
    [string]::IsNullOrWhiteSpace($env:TAURI_SIGNING_PRIVATE_KEY) -and
    [string]::IsNullOrWhiteSpace($env:TAURI_SIGNING_PRIVATE_KEY_PATH)
) {
    throw "Set TAURI_SIGNING_PRIVATE_KEY_PATH (recommended) or TAURI_SIGNING_PRIVATE_KEY for a formal release."
}
if ([string]::IsNullOrWhiteSpace($UpdaterPublicKey)) {
    throw "Set OXO_UPDATER_PUBLIC_KEY or pass -UpdaterPublicKey for a formal release."
}
if (!$AllowDirty) {
    $status = git -C $WorkspaceRoot status --porcelain
    if ($LASTEXITCODE -ne 0) { throw "Unable to inspect the Git worktree" }
    if ($status) { throw "Formal desktop releases require a clean Git worktree. Commit or stash changes, or use -AllowDirty only for controlled testing." }
}

$arguments = @{
    Version = $Version
    CertificateThumbprint = $CertificateThumbprint
    TimestampUrl = $TimestampUrl
    UpdaterPublicKey = $UpdaterPublicKey
    UpdaterEndpoint = $UpdaterEndpoint
    SkipTests = $SkipTests
}
& (Join-Path $PSScriptRoot "build-desktop.ps1") @arguments
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Review artifacts locally, then create the GitHub Release manually at:"
Write-Host "https://github.com/Oxo-AI-Security/Oxo-Tracker-Releases/releases/new"
