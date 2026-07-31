param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$')]
    [string]$Version,
    [string]$CertificateThumbprint = $env:OXO_SIGNING_CERT_THUMBPRINT,
    [string]$TimestampUrl = "http://timestamp.digicert.com",
    [switch]$SkipTests,
    [switch]$AllowDirty
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = [IO.Path]::GetFullPath((Split-Path $PSScriptRoot -Parent))

if (!$CertificateThumbprint) {
    throw "Set OXO_SIGNING_CERT_THUMBPRINT or pass -CertificateThumbprint for a formal release."
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
    SkipTests = $SkipTests
}
& (Join-Path $PSScriptRoot "build-desktop.ps1") @arguments
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Review artifacts locally, then create the GitHub Release manually at:"
Write-Host "https://github.com/Oxo-AI-Security/Oxo-Tracker-Releases/releases/new"
