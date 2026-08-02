param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version,
    [string]$WorkspaceRoot,
    [switch]$MarkVerified
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $WorkspaceRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\..\.."))
}
else { $WorkspaceRoot = [IO.Path]::GetFullPath($WorkspaceRoot) }
$releaseDirectory = Join-Path $WorkspaceRoot "artifacts\desktop-release\$Version"
$installerName = "Oxo-Tracker_${Version}_x64-setup.exe"
$expectedNames = @(
    $installerName,
    "$installerName.sig",
    "$installerName.sha256",
    "latest.json",
    "RELEASE-NOTES.md",
    "BUILD-INFO.json",
    "dataset-manifest.json",
    "sbom.spdx.json",
    "THIRD-PARTY-NOTICES.txt"
)
$actualNames = @(Get-ChildItem -LiteralPath $releaseDirectory -File | Select-Object -ExpandProperty Name | Sort-Object)
$missing = @($expectedNames | Where-Object { $_ -notin $actualNames })
$unexpected = @($actualNames | Where-Object { $_ -notin $expectedNames })
if ($missing.Count -gt 0 -or $unexpected.Count -gt 0) {
    throw "Release asset set mismatch. Missing: $($missing -join ', '); unexpected: $($unexpected -join ', ')"
}

$installer = Join-Path $releaseDirectory $installerName
if ((Get-Item -LiteralPath $installer).Length -gt 350MB) { throw "Installer exceeds the 350 MiB release gate." }
$hash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLowerInvariant()
$checksum = ((Get-Content -LiteralPath "$installer.sha256" -Raw -Encoding ASCII) -split '\s+')[0].ToLowerInvariant()
if ($hash -ne $checksum) { throw "Installer SHA-256 does not match its checksum file." }

$latest = Get-Content -LiteralPath (Join-Path $releaseDirectory "latest.json") -Raw -Encoding UTF8 | ConvertFrom-Json
if ($latest.version -ne $Version) { throw "latest.json version is $($latest.version), expected $Version." }
$platform = $latest.platforms.'windows-x86_64'
$expectedUrl = "https://github.com/Oxo-AI-Security/Oxo-Tracker-Releases/releases/download/v$Version/$installerName"
if ($platform.url -ne $expectedUrl) { throw "latest.json installer URL is not canonical: $($platform.url)" }
$signature = (Get-Content -LiteralPath "$installer.sig" -Raw -Encoding UTF8).Trim()
if ($platform.signature -ne $signature) { throw "latest.json signature does not match the .sig file." }

$datasetManifest = Get-Content -LiteralPath (Join-Path $releaseDirectory "dataset-manifest.json") -Raw -Encoding UTF8 | ConvertFrom-Json
if ([int]$datasetManifest.datasetCount -le 0 -or @($datasetManifest.datasets).Count -ne [int]$datasetManifest.datasetCount) {
    throw "Moonshot dataset manifest count is invalid."
}
$buildInfoPath = Join-Path $releaseDirectory "BUILD-INFO.json"
$buildInfo = Get-Content -LiteralPath $buildInfoPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($buildInfo.version -ne $Version -or $buildInfo.installer_sha256 -ne $hash) { throw "BUILD-INFO.json does not match the installer." }
if ([int]$buildInfo.dataset_json_files -ne [int]$datasetManifest.datasetCount) { throw "BUILD-INFO Moonshot count does not match dataset-manifest.json." }
$versionInfo = [Diagnostics.FileVersionInfo]::GetVersionInfo($installer)
if ($versionInfo.ProductVersion -notmatch "^$([regex]::Escape($Version))(?:\D|$)" -or $versionInfo.FileVersion -notmatch "^$([regex]::Escape($Version))(?:\D|$)") {
    throw "Installer product/file version does not match $Version."
}

$toolRoot = Join-Path $WorkspaceRoot ".desktop-build\release-tools"
New-Item -ItemType Directory -Path $toolRoot -Force | Out-Null
$publicKeyText = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String((Get-Content -LiteralPath (Join-Path $WorkspaceRoot "frontend\src-tauri\updater.pubkey") -Raw).Trim()))
$signatureText = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($signature))
$decodedPublicKey = Join-Path $toolRoot "updater.pub"
$decodedSignature = Join-Path $toolRoot "installer.sig"
[IO.File]::WriteAllText($decodedPublicKey, $publicKeyText, [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText($decodedSignature, $signatureText, [Text.UTF8Encoding]::new($false))

. (Join-Path $WorkspaceRoot "scripts\desktop-toolchain.ps1")
$null = Initialize-OxoDesktopToolchain -WorkspaceRoot $WorkspaceRoot
$cargoManifest = Join-Path $PSScriptRoot "verify-updater\Cargo.toml"
$targetDirectory = Join-Path $toolRoot "verify-updater-target"
& cargo run --quiet --release --target-dir $targetDirectory --manifest-path $cargoManifest -- $decodedPublicKey $decodedSignature $installer
if ($LASTEXITCODE -ne 0) { throw "Cryptographic updater signature verification failed." }

if ($MarkVerified) {
    $buildInfo.updater_signature_verified = $true
    $buildInfo | Add-Member -NotePropertyName signature_verified_at -NotePropertyValue ([DateTimeOffset]::UtcNow.ToString("o")) -Force
    [IO.File]::WriteAllText($buildInfoPath, (($buildInfo | ConvertTo-Json -Depth 10) + [Environment]::NewLine), [Text.UTF8Encoding]::new($false))
}

[pscustomobject]@{
    version = $Version
    source_commit = $buildInfo.source_commit
    installer = $installer
    installer_bytes = (Get-Item -LiteralPath $installer).Length
    sha256 = $hash
    authenticode_status = [string](Get-AuthenticodeSignature -LiteralPath $installer).Status
    updater_signature_verified = $true
    dataset_json_files = [int]$datasetManifest.datasetCount
} | ConvertTo-Json -Depth 4
