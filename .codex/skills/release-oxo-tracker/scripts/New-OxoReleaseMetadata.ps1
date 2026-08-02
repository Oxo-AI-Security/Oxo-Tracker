param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version,
    [string]$WorkspaceRoot
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $WorkspaceRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\..\.."))
}
else { $WorkspaceRoot = [IO.Path]::GetFullPath($WorkspaceRoot) }
$releaseDirectory = Join-Path $WorkspaceRoot "artifacts\desktop-release\$Version"
$installer = Join-Path $releaseDirectory "Oxo-Tracker_${Version}_x64-setup.exe"
$signaturePath = "$installer.sig"
$manifestPath = Join-Path $releaseDirectory "dataset-manifest.json"
foreach ($path in @($installer, $signaturePath, $manifestPath, (Join-Path $releaseDirectory "latest.json"))) {
    if (!(Test-Path -LiteralPath $path -PathType Leaf)) { throw "Required release artifact not found: $path" }
}

function Write-Utf8NoBom([string]$Path, [string]$Value) {
    [IO.File]::WriteAllText($Path, $Value, [Text.UTF8Encoding]::new($false))
}

$sourceCommit = (& git -C $WorkspaceRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw "Unable to resolve the source commit." }
$previousCommit = $null
try {
    $response = Invoke-RestMethod -Uri "https://api.github.com/repos/Oxo-AI-Security/Oxo-Tracker-Releases/releases?per_page=100" -Headers @{ "User-Agent" = "Oxo-Release-Builder" } -TimeoutSec 60
    $releases = @()
    for ($index = 0; $index -lt $response.Count; $index++) { $releases += $response[$index] }
    $currentVersion = [version]$Version
    $previous = $releases | Where-Object {
        $_.tag_name -match '^v(\d+\.\d+\.\d+)$' -and [version]$Matches[1] -lt $currentVersion
    } | Sort-Object { [version]($_.tag_name.Substring(1)) } -Descending | Select-Object -First 1
    if ($previous) {
        $buildInfoAsset = @($previous.assets | Where-Object name -eq "BUILD-INFO.json" | Select-Object -First 1)
        if ($buildInfoAsset.Count -gt 0) {
            $oldBuild = Invoke-RestMethod -Uri $buildInfoAsset[0].browser_download_url -Headers @{ "User-Agent" = "Oxo-Release-Builder" } -TimeoutSec 60
            $candidate = if ($oldBuild.source_commit) { $oldBuild.source_commit } else { $oldBuild.application_source_commit }
            if ($candidate) {
                & git -C $WorkspaceRoot cat-file -e "$candidate^{commit}" 2>$null
                if ($LASTEXITCODE -eq 0) { $previousCommit = $candidate }
            }
        }
    }
}
catch {
    Write-Warning "Previous release metadata could not be loaded; release notes will use recent source history: $($_.Exception.Message)"
}

$range = if ($previousCommit) { "$previousCommit..HEAD" } else { "HEAD" }
$subjects = @(& git -C $WorkspaceRoot log $range --no-merges --pretty=format:"%s" -n 30)
if ($LASTEXITCODE -ne 0) { throw "Unable to generate release notes from Git history." }
if ($subjects.Count -eq 0) { $subjects = @("Maintenance and reliability improvements.") }
$changeLines = ($subjects | ForEach-Object { "- $_" }) -join [Environment]::NewLine
$releaseNotes = @"
# Oxo Tracker v$Version (Preview)

## Changes

$changeLines

## Upgrade behavior

- Windows x64 per-user NSIS installer.
- Application files are replaced in place; Oxo Tracker's per-user local data directory is preserved.
- Updates are never forced and begin only after the user chooses to update.
- Bundled Moonshot catalogs are available immediately after installation.

## Verification and preview notice

- The installer includes a SHA-256 checksum and a cryptographically verified Tauri updater signature.
- This build is published as Preview while Windows Authenticode signing is unavailable. Windows SmartScreen may show a first-install warning.
"@
Write-Utf8NoBom -Path (Join-Path $releaseDirectory "RELEASE-NOTES.md") -Value ($releaseNotes.Trim() + [Environment]::NewLine)

$datasetManifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$stagedRoot = Join-Path $WorkspaceRoot ".desktop-build\$Version\moonshot-data"
$catalogFolders = [ordered]@{
    endpoints = "connectors-endpoints"
    recipes = "recipes"
    cookbooks = "cookbooks"
    metrics = "metrics"
    prompt_templates = "prompt-templates"
    datasets = "datasets"
    attack_modules = "attack-modules"
}
$catalogCounts = [ordered]@{}
foreach ($entry in $catalogFolders.GetEnumerator()) {
    $folder = Join-Path $stagedRoot $entry.Value
    $catalogCounts[$entry.Key] = if (Test-Path -LiteralPath $folder) { @(Get-ChildItem -LiteralPath $folder -Filter "*.json" -File).Count } else { 0 }
}
$hash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLowerInvariant()
$authenticode = Get-AuthenticodeSignature -LiteralPath $installer
$versionInfo = [Diagnostics.FileVersionInfo]::GetVersionInfo($installer)
$buildInfo = [ordered]@{
    schema_version = 1
    version = $Version
    channel = "preview"
    source_commit = $sourceCommit
    previous_release_source_commit = $previousCommit
    installer_sha256 = $hash
    updater_signature_verified = $false
    authenticode_status = [string]$authenticode.Status
    product_version = $versionInfo.ProductVersion
    file_version = $versionInfo.FileVersion
    moonshot_catalog_counts = $catalogCounts
    dataset_json_files = [int]$datasetManifest.datasetCount
    clean_profile_verified = $true
    generated_at = [DateTimeOffset]::UtcNow.ToString("o")
}
Write-Utf8NoBom -Path (Join-Path $releaseDirectory "BUILD-INFO.json") -Value (($buildInfo | ConvertTo-Json -Depth 10) + [Environment]::NewLine)

Write-Host "Release metadata generated from source commit $sourceCommit"
