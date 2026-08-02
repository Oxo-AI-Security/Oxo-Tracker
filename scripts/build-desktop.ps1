param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$')]
    [string]$Version,
    [string]$CertificateThumbprint = $env:OXO_SIGNING_CERT_THUMBPRINT,
    [string]$TimestampUrl = "http://timestamp.digicert.com",
    [string]$UpdaterPublicKey = $env:OXO_UPDATER_PUBLIC_KEY,
    [string]$UpdaterEndpoint = "https://oxotracker.oss-cn-beijing.aliyuncs.com/stable/latest.json",
    [switch]$SkipTests,
    [switch]$AllowUnsigned
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$WorkspaceRoot = [IO.Path]::GetFullPath((Split-Path $PSScriptRoot -Parent))
$BuildRoot = [IO.Path]::GetFullPath((Join-Path $WorkspaceRoot ".desktop-build"))
$BuildDirectory = [IO.Path]::GetFullPath((Join-Path $BuildRoot $Version))
$Wheelhouse = Join-Path $BuildRoot "wheelhouse"
$FrontendRoot = Join-Path $WorkspaceRoot "frontend"
$TauriRoot = Join-Path $FrontendRoot "src-tauri"
$ResourceDirectory = Join-Path $TauriRoot "resources"
$BinaryDirectory = Join-Path $TauriRoot "binaries"
$MoonshotSource = Join-Path $WorkspaceRoot "data\moonshot-data"
$PolicyPath = Join-Path $WorkspaceRoot "desktop\asset-policy.json"
$ReleaseDirectory = Join-Path $WorkspaceRoot "artifacts\desktop-release\$Version"
. (Join-Path $PSScriptRoot "desktop-toolchain.ps1")

$defaultUpdaterPublicKeyPath = Join-Path $TauriRoot "updater.pubkey"
if ([string]::IsNullOrWhiteSpace($UpdaterPublicKey) -and (Test-Path -LiteralPath $defaultUpdaterPublicKeyPath -PathType Leaf)) {
    $UpdaterPublicKey = $defaultUpdaterPublicKeyPath
}
$hasUpdaterPrivateKey = (
    ![string]::IsNullOrWhiteSpace($env:TAURI_SIGNING_PRIVATE_KEY) -or
    ![string]::IsNullOrWhiteSpace($env:TAURI_SIGNING_PRIVATE_KEY_PATH)
)
$hasUpdaterPublicKey = ![string]::IsNullOrWhiteSpace($UpdaterPublicKey)
if ($hasUpdaterPrivateKey -xor $hasUpdaterPublicKey) {
    throw "Tauri updater signing requires TAURI_SIGNING_PRIVATE_KEY or TAURI_SIGNING_PRIVATE_KEY_PATH, plus OXO_UPDATER_PUBLIC_KEY (or -UpdaterPublicKey)."
}
if ($hasUpdaterPublicKey -and $UpdaterPublicKey -notmatch '[\r\n]' -and (Test-Path -LiteralPath $UpdaterPublicKey -PathType Leaf)) {
    $UpdaterPublicKey = (Get-Content -LiteralPath $UpdaterPublicKey -Raw -Encoding UTF8).Trim()
}

function Assert-WithinDirectory {
    param([string]$Path, [string]$Parent)
    $fullPath = [IO.Path]::GetFullPath($Path).TrimEnd('\')
    $fullParent = [IO.Path]::GetFullPath($Parent).TrimEnd('\')
    if (!$fullPath.StartsWith("$fullParent\", [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to modify a path outside $fullParent`: $fullPath"
    }
}

function Reset-Directory {
    param([string]$Path, [string]$AllowedParent)
    Assert-WithinDirectory -Path $Path -Parent $AllowedParent
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}

function Invoke-Checked {
    param([string]$FilePath, [string[]]$Arguments, [string]$WorkingDirectory = $WorkspaceRoot)
    Push-Location $WorkingDirectory
    try {
        & $FilePath @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "$FilePath failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }
}

function Get-VerifiedDownload {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$Destination,
        [Parameter(Mandatory = $true)][string]$Sha256
    )
    if (Test-Path -LiteralPath $Destination -PathType Leaf) {
        $existingHash = (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($existingHash -eq $Sha256) { return }
        Remove-Item -LiteralPath $Destination -Force
    }
    $partial = "$Destination.partial"
    if (Test-Path -LiteralPath $partial -PathType Leaf) {
        Remove-Item -LiteralPath $partial -Force
    }
    $curl = Get-Command "curl.exe" -ErrorAction SilentlyContinue
    if ($curl) {
        Invoke-Checked -FilePath $curl.Source -Arguments @(
            "--fail", "--location", "--retry", "5", "--retry-delay", "2",
            "--connect-timeout", "15", "--max-time", "300",
            "--speed-time", "30", "--speed-limit", "1024",
            "--output", $partial, $Url
        )
    }
    else {
        Invoke-WebRequest -Uri $Url -OutFile $partial -UseBasicParsing -TimeoutSec 120
    }
    $actualHash = (Get-FileHash -LiteralPath $partial -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualHash -ne $Sha256) {
        Remove-Item -LiteralPath $partial -Force
        throw "SHA-256 mismatch for $Url. Expected $Sha256, received $actualHash."
    }
    Move-Item -LiteralPath $partial -Destination $Destination
}

function Find-SignTool {
    $command = Get-Command "signtool.exe" -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $kitsRoot = "${env:ProgramFiles(x86)}\Windows Kits\10\bin"
    if (Test-Path -LiteralPath $kitsRoot) {
        $candidate = Get-ChildItem -LiteralPath $kitsRoot -Filter "signtool.exe" -File -Recurse |
            Where-Object { $_.FullName -match '\\x64\\signtool\.exe$' } |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($candidate) { return $candidate.FullName }
    }
    throw "signtool.exe was not found. Install the Windows SDK signing tools."
}

function Sign-File {
    param([string]$Path, [string]$Thumbprint)
    $signTool = Find-SignTool
    Invoke-Checked -FilePath $signTool -Arguments @(
        "sign", "/sha1", $Thumbprint, "/fd", "sha256", "/tr", $TimestampUrl, "/td", "sha256", $Path
    )
    Invoke-Checked -FilePath $signTool -Arguments @("verify", "/pa", "/v", $Path)
}

function Clear-EndpointSecrets {
    param([object]$Value)
    $placeholders = @("", "Use environment variables!", "your h2ogpte api key", "flageval_judgemodel", "ollama")
    if ($Value -is [System.Management.Automation.PSCustomObject]) {
        foreach ($property in @($Value.PSObject.Properties)) {
            $normalized = ($property.Name.ToLowerInvariant() -replace '[^a-z]', '')
            if ($normalized -in @("token", "apikey", "password", "secret", "authorization")) {
                if ($property.Value -is [string] -and $property.Value -notin $placeholders) {
                    $property.Value = ""
                }
            }
            else {
                Clear-EndpointSecrets -Value $property.Value
            }
        }
    }
    elseif ($Value -is [System.Collections.IEnumerable] -and $Value -isnot [string]) {
        foreach ($item in $Value) { Clear-EndpointSecrets -Value $item }
    }
}

function Test-Sidecar {
    param([string]$Executable, [string]$ResourceRoot, [string]$AppHome)
    $token = ([guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N"))
    $challenge = [guid]::NewGuid().ToString("N")
    $startInfo = [Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $Executable
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $arguments = @(
        "--token", $token,
        "--resource-root", $ResourceRoot,
        "--app-home", $AppHome,
        "--asset-version", $Version
    )
    # Windows PowerShell 5.1 exposes ProcessStartInfo.ArgumentList as null.
    # Quote these controlled arguments explicitly so the release script works
    # in both Windows PowerShell and PowerShell 7.
    $startInfo.Arguments = ($arguments | ForEach-Object {
        '"' + ([string]$_).Replace('"', '\"') + '"'
    }) -join ' '
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    [void]$process.Start()
    try {
        $ready = $null
        $deadline = [DateTime]::UtcNow.AddSeconds(90)
        while ([DateTime]::UtcNow -lt $deadline -and !$ready) {
            $readTask = $process.StandardOutput.ReadLineAsync()
            if (!$readTask.Wait(90000)) { throw "Timed out waiting for the sidecar ready message" }
            $line = $readTask.Result
            if ($null -eq $line) { break }
            if ($line.StartsWith("OXO_DESKTOP_READY ")) {
                $ready = $line.Substring("OXO_DESKTOP_READY ".Length) | ConvertFrom-Json
            }
        }
        if (!$ready) {
            $stderr = $process.StandardError.ReadToEnd()
            throw "Sidecar did not emit a ready message. $stderr"
        }
        $uri = "http://127.0.0.1:$($ready.port)/health?challenge=$challenge"
        $response = $null
        for ($attempt = 0; $attempt -lt 80 -and !$response; $attempt++) {
            try {
                $response = Invoke-RestMethod -Uri $uri -Headers @{ "X-Oxo-Desktop-Token" = $token } -TimeoutSec 2
            }
            catch {
                Start-Sleep -Milliseconds 100
            }
        }
        if (!$response -or $response.status -ne "ok" -or $response.challenge -ne $challenge) {
            throw "Sidecar health challenge failed"
        }
    }
    finally {
        if (!$process.HasExited) { $process.Kill() }
        $process.Dispose()
    }
}

if (!(Test-Path -LiteralPath $MoonshotSource)) {
    throw "Moonshot data was not found at $MoonshotSource"
}
if (!$CertificateThumbprint -and !$AllowUnsigned) {
    throw "A code-signing certificate is required. Set OXO_SIGNING_CERT_THUMBPRINT or pass -AllowUnsigned for a non-release build."
}
if (!(Get-Command "npm" -ErrorAction SilentlyContinue)) {
    throw "npm is required for desktop builds but was not found on PATH"
}
$UsePortableMsvc = Initialize-OxoDesktopToolchain -WorkspaceRoot $WorkspaceRoot

Reset-Directory -Path $BuildDirectory -AllowedParent $BuildRoot
Reset-Directory -Path $ReleaseDirectory -AllowedParent (Join-Path $WorkspaceRoot "artifacts\desktop-release")

$DevelopmentPython = Join-Path $WorkspaceRoot ".venv\Scripts\python.exe"
if (!(Test-Path -LiteralPath $DevelopmentPython)) {
    throw "Run scripts/bootstrap.ps1 first so backend tests have a development Python environment."
}
if (!$SkipTests) {
    Invoke-Checked -FilePath $DevelopmentPython -Arguments @("-m", "pytest")
    Invoke-Checked -FilePath "npm" -Arguments @("test") -WorkingDirectory $FrontendRoot
    Invoke-Checked -FilePath "npm" -Arguments @("run", "build") -WorkingDirectory $FrontendRoot
}

$ReleaseVenv = Join-Path $BuildDirectory "venv"
Invoke-Checked -FilePath $DevelopmentPython -Arguments @("-m", "venv", $ReleaseVenv)
$ReleasePython = Join-Path $ReleaseVenv "Scripts\python.exe"
$pipArguments = @(
    "-m", "pip", "install",
    "--disable-pip-version-check",
    "--timeout", "120",
    "--retries", "10",
    "-r", (Join-Path $WorkspaceRoot "requirements-desktop.lock"),
    "-r", (Join-Path $WorkspaceRoot "requirements-desktop-build.txt")
)
if (Test-Path -LiteralPath $Wheelhouse) {
    $pipArguments += @("--find-links", $Wheelhouse)
}
Invoke-Checked -FilePath $ReleasePython -Arguments $pipArguments

$policy = Get-Content -LiteralPath $PolicyPath -Raw | ConvertFrom-Json
$installed = (& $ReleasePython -m pip list --format=json | ConvertFrom-Json).name
$forbiddenFound = @($policy.forbiddenDistributions | Where-Object { $_ -in $installed })
if ($forbiddenFound.Count -gt 0) {
    throw "Desktop environment contains forbidden local-model packages: $($forbiddenFound -join ', ')"
}

$StagedAssets = Join-Path $BuildDirectory "moonshot-data"
New-Item -ItemType Directory -Path $StagedAssets -Force | Out-Null
$assetFolders = @(
    "attack-modules", "connectors", "connectors-endpoints", "context-strategy", "cookbooks",
    "databases-modules", "datasets", "io-modules", "metrics", "prompt-templates", "recipes",
    "results-modules", "runners-modules", "third-party"
)
foreach ($folder in $assetFolders) {
    Copy-Item -LiteralPath (Join-Path $MoonshotSource $folder) -Destination (Join-Path $StagedAssets $folder) -Recurse
}
foreach ($file in @("AUTHORS.md", "LICENSE.md", "NOTICES.md", "README.md")) {
    Copy-Item -LiteralPath (Join-Path $MoonshotSource $file) -Destination (Join-Path $StagedAssets $file)
}
$generatedOutput = Join-Path $StagedAssets "generated-outputs"
foreach ($folder in @("bookmarks", "databases", "reports", "results", "runners")) {
    $outputFolder = Join-Path $generatedOutput $folder
    New-Item -ItemType Directory -Path $outputFolder -Force | Out-Null
    New-Item -ItemType File -Path (Join-Path $outputFolder "placeholder") -Force | Out-Null
}
foreach ($relative in $policy.excludedAssets) {
    $target = [IO.Path]::GetFullPath((Join-Path $StagedAssets $relative))
    Assert-WithinDirectory -Path $target -Parent $StagedAssets
    if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Force }
}
foreach ($name in $policy.excludedRecipes) {
    $target = [IO.Path]::GetFullPath((Join-Path $StagedAssets "recipes\$name"))
    Assert-WithinDirectory -Path $target -Parent $StagedAssets
    if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Force }
}
foreach ($endpointPath in Get-ChildItem -LiteralPath (Join-Path $StagedAssets "connectors-endpoints") -Filter "*.json" -File) {
    $endpoint = Get-Content -LiteralPath $endpointPath.FullName -Raw | ConvertFrom-Json
    Clear-EndpointSecrets -Value $endpoint
    $endpoint | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $endpointPath.FullName -Encoding UTF8
}

$DatasetManifest = Join-Path $BuildDirectory "dataset-manifest.json"
Invoke-Checked -FilePath $ReleasePython -Arguments @(
    (Join-Path $WorkspaceRoot "scripts\verify_desktop_assets.py"),
    "--source", $MoonshotSource,
    "--staged", $StagedAssets,
    "--policy", $PolicyPath,
    "--manifest", $DatasetManifest
)
Copy-Item -LiteralPath $DatasetManifest -Destination (Join-Path $StagedAssets ".oxo-dataset-manifest.json")

$MoonshotArchive = Join-Path $BuildDirectory "moonshot-data.zip"
Add-Type -AssemblyName System.IO.Compression.FileSystem
[IO.Compression.ZipFile]::CreateFromDirectory($StagedAssets, $MoonshotArchive, [IO.Compression.CompressionLevel]::Optimal, $false)
Copy-Item -LiteralPath $MoonshotArchive -Destination (Join-Path $ResourceDirectory "moonshot-data.zip") -Force

$NltkData = Join-Path $ResourceDirectory "nltk_data"
if (Test-Path -LiteralPath $NltkData) {
    Assert-WithinDirectory -Path $NltkData -Parent $ResourceDirectory
    Remove-Item -LiteralPath $NltkData -Recurse -Force
}
New-Item -ItemType Directory -Path $NltkData -Force | Out-Null
$NltkCache = Join-Path $BuildRoot "nltk-cache"
New-Item -ItemType Directory -Path $NltkCache -Force | Out-Null
$NltkPackages = @(
    @{ Category = "tokenizers"; Id = "punkt"; Sha256 = "51c3078994aeaf650bfc8e028be4fb42b4a0d177d41c012b6a983979653660ec" },
    @{ Category = "tokenizers"; Id = "punkt_tab"; Sha256 = "e57f64187974277726a3417ca6f181ec5403676c717672eef6a748a7b20e0106" },
    @{ Category = "taggers"; Id = "averaged_perceptron_tagger_eng"; Sha256 = "6025f530624335c67d6547d44757b357b4e79bae030a0383e9887a92c1718f0b" },
    @{ Category = "corpora"; Id = "stopwords"; Sha256 = "48c0e52d8b52546e827f53761fb30300c0ab94f70660d28bd65ba0a86270946b" }
)
foreach ($package in $NltkPackages) {
    $archive = Join-Path $NltkCache "$($package.Id).zip"
    if (!(Test-Path -LiteralPath $archive -PathType Leaf)) {
        $localCandidates = @(
            (Join-Path $env:APPDATA "nltk_data\$($package.Category)\$($package.Id).zip"),
            (Join-Path $env:LOCALAPPDATA "nltk_data\$($package.Category)\$($package.Id).zip"),
            (Join-Path $env:USERPROFILE "nltk_data\$($package.Category)\$($package.Id).zip")
        )
        foreach ($candidate in $localCandidates) {
            if (!(Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
            $candidateHash = (Get-FileHash -LiteralPath $candidate -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($candidateHash -eq $package.Sha256) {
                Copy-Item -LiteralPath $candidate -Destination $archive
                break
            }
        }
    }
    # jsDelivr serves the exact nltk/nltk_data gh-pages objects; the official
    # nltk_data index SHA-256 below remains the source of truth.
    $url = "https://cdn.jsdelivr.net/gh/nltk/nltk_data@gh-pages/packages/$($package.Category)/$($package.Id).zip"
    Get-VerifiedDownload -Url $url -Destination $archive -Sha256 $package.Sha256
    $categoryDirectory = Join-Path $NltkData $package.Category
    New-Item -ItemType Directory -Path $categoryDirectory -Force | Out-Null
    Expand-Archive -LiteralPath $archive -DestinationPath $categoryDirectory -Force
}
# The spec rejects host-profile nltk_data discovered by PyInstaller's upstream
# hook. Runtime NLTK_DATA points only at these pinned, hash-verified resources.

$MetadataDirectory = Join-Path $BuildDirectory "metadata"
Invoke-Checked -FilePath $ReleasePython -Arguments @(
    (Join-Path $WorkspaceRoot "scripts\generate_desktop_release_metadata.py"),
    "--version", $Version,
    "--dataset-manifest", $DatasetManifest,
    "--output", $MetadataDirectory
)
Copy-Item -LiteralPath (Join-Path $MetadataDirectory "THIRD-PARTY-NOTICES.txt") -Destination (Join-Path $ResourceDirectory "THIRD-PARTY-NOTICES.txt") -Force

$PyInstallerDist = Join-Path $BuildDirectory "pyinstaller\dist"
$PyInstallerWork = Join-Path $BuildDirectory "pyinstaller\work"
Invoke-Checked -FilePath $ReleasePython -Arguments @(
    "-m", "PyInstaller",
    "--noconfirm", "--clean",
    "--distpath", $PyInstallerDist,
    "--workpath", $PyInstallerWork,
    (Join-Path $WorkspaceRoot "desktop\oxo-backend.spec")
)
$BuiltSidecarDirectory = Join-Path $PyInstallerDist "oxo-backend"
$BuiltSidecar = Join-Path $BuiltSidecarDirectory "oxo-backend.exe"
if (!(Test-Path -LiteralPath $BuiltSidecar)) { throw "PyInstaller did not create $BuiltSidecar" }
if ($CertificateThumbprint) { Sign-File -Path $BuiltSidecar -Thumbprint $CertificateThumbprint }

$TargetSidecar = Join-Path $BinaryDirectory "oxo-backend-x86_64-pc-windows-msvc.exe"
Copy-Item -LiteralPath $BuiltSidecar -Destination $TargetSidecar -Force
$TargetLibrary = Join-Path $BinaryDirectory "oxo-backend-lib"
Get-ChildItem -LiteralPath $TargetLibrary -Force | Where-Object { $_.Name -ne ".gitkeep" } | ForEach-Object {
    Remove-Item -LiteralPath $_.FullName -Recurse -Force
}
Copy-Item -Path (Join-Path $BuiltSidecarDirectory "oxo-backend-lib\*") -Destination $TargetLibrary -Recurse -Force

$SmokeHome = Join-Path $BuildDirectory "smoke-user-data"
New-Item -ItemType Directory -Path $SmokeHome -Force | Out-Null
Test-Sidecar -Executable $BuiltSidecar -ResourceRoot $ResourceDirectory -AppHome $SmokeHome

$releaseConfig = @{
    version = $Version
    bundle = @{ windows = @{} }
}
if ($hasUpdaterPublicKey) {
    $releaseConfig.bundle.createUpdaterArtifacts = $true
    $releaseConfig.plugins = @{
        updater = @{
            pubkey = $UpdaterPublicKey
            endpoints = @($UpdaterEndpoint)
            windows = @{ installMode = "passive" }
        }
    }
}
if ($CertificateThumbprint) {
    $releaseConfig.bundle.windows.certificateThumbprint = $CertificateThumbprint
    $releaseConfig.bundle.windows.digestAlgorithm = "sha256"
    $releaseConfig.bundle.windows.timestampUrl = $TimestampUrl
}
$TauriReleaseConfig = Join-Path $BuildDirectory "tauri.release.conf.json"
$releaseConfig | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $TauriReleaseConfig -Encoding UTF8
$tauriArguments = @("run", "tauri", "--", "build", "--bundles", "nsis", "--config", $TauriReleaseConfig)
if ($UsePortableMsvc) {
    $tauriArguments += @("--target", "x86_64-pc-windows-msvc")
}
$tauriBuildStartedAt = [DateTime]::UtcNow.AddSeconds(-2)
$tauriBuildError = $null
try {
    Invoke-Checked -FilePath "npm" -Arguments $tauriArguments -WorkingDirectory $FrontendRoot
}
catch {
    # Some Windows CLI versions can finish the fresh NSIS installer and then
    # fail while creating its updater signature. A deterministic signer
    # fallback below may recover that specific post-bundle failure.
    $tauriBuildError = $_
}

$bundleRoot = if ($UsePortableMsvc) {
    Join-Path $TauriRoot "target\x86_64-pc-windows-msvc\release\bundle\nsis"
}
else {
    Join-Path $TauriRoot "target\release\bundle\nsis"
}
$installer = Get-ChildItem -LiteralPath $bundleRoot -Filter "*_${Version}_x64-setup.exe" -File |
    Where-Object { $_.LastWriteTimeUtc -ge $tauriBuildStartedAt } |
    Sort-Object LastWriteTimeUtc -Descending |
    Select-Object -First 1
if (!$installer) {
    if ($tauriBuildError) { throw $tauriBuildError }
    throw "Tauri did not produce a fresh NSIS installer for $Version"
}
if ($hasUpdaterPublicKey -and !(Test-Path -LiteralPath "$($installer.FullName).sig" -PathType Leaf)) {
    Write-Warning "Tauri did not emit the updater signature during bundling; signing the fresh installer explicitly."
    Invoke-Checked -FilePath "npm" -Arguments @(
        "run", "tauri", "--", "signer", "sign", $installer.FullName
    ) -WorkingDirectory $FrontendRoot
}
if ($tauriBuildError) {
    Write-Warning "Tauri bundling returned an error after producing the installer; explicit updater signing recovered the release."
}
$releaseInstaller = Join-Path $ReleaseDirectory "Oxo-Tracker_${Version}_x64-setup.exe"
Copy-Item -LiteralPath $installer.FullName -Destination $releaseInstaller -Force
if ((Get-Item -LiteralPath $releaseInstaller).Length -gt 350MB) {
    throw "Installer exceeds the 350 MiB release gate: $releaseInstaller"
}

$hash = (Get-FileHash -LiteralPath $releaseInstaller -Algorithm SHA256).Hash.ToLowerInvariant()
"$hash  $(Split-Path $releaseInstaller -Leaf)" | Set-Content -LiteralPath "$releaseInstaller.sha256" -Encoding ASCII
if ($hasUpdaterPublicKey) {
    $installerSignature = "$($installer.FullName).sig"
    if (!(Test-Path -LiteralPath $installerSignature -PathType Leaf)) {
        throw "Tauri did not produce the updater signature: $installerSignature"
    }
    $releaseSignature = "$releaseInstaller.sig"
    Copy-Item -LiteralPath $installerSignature -Destination $releaseSignature -Force
}
Copy-Item -LiteralPath $DatasetManifest -Destination (Join-Path $ReleaseDirectory "dataset-manifest.json")
Copy-Item -LiteralPath (Join-Path $MetadataDirectory "THIRD-PARTY-NOTICES.txt") -Destination $ReleaseDirectory
Copy-Item -LiteralPath (Join-Path $MetadataDirectory "sbom.spdx.json") -Destination $ReleaseDirectory
@"
# Oxo Tracker $Version

- Windows x64 per-user NSIS installer.
- Includes all 222 approved Moonshot datasets.
- Uses user-configured online model APIs only; no local model runtime or weights are included.
- Built and verified locally. Upload the files in this directory manually to Oxo-Tracker-Releases.
"@ | Set-Content -LiteralPath (Join-Path $ReleaseDirectory "RELEASE-NOTES.md") -Encoding UTF8

if ($hasUpdaterPublicKey) {
    $signature = (Get-Content -LiteralPath "$releaseInstaller.sig" -Raw -Encoding UTF8).Trim()
    $manifest = [ordered]@{
        version = $Version
        notes = "Oxo Tracker $Version"
        pub_date = [DateTimeOffset]::UtcNow.ToString("o")
        platforms = [ordered]@{
            "windows-x86_64" = [ordered]@{
                url = "https://github.com/Oxo-AI-Security/Oxo-Tracker-Releases/releases/download/v$Version/Oxo-Tracker_${Version}_x64-setup.exe"
                signature = $signature
            }
        }
    }
    $manifestPath = Join-Path $ReleaseDirectory "latest.json"
    [IO.File]::WriteAllText(
        $manifestPath,
        ($manifest | ConvertTo-Json -Depth 10),
        [Text.UTF8Encoding]::new($false)
    )
}

Write-Host "Desktop release artifacts are ready: $ReleaseDirectory"
Get-ChildItem -LiteralPath $ReleaseDirectory | Select-Object Name, Length
