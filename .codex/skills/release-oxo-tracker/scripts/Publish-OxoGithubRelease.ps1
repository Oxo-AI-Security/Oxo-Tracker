param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version,
    [string]$WorkspaceRoot,
    [string]$Repository = "Oxo-AI-Security/Oxo-Tracker-Releases"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $WorkspaceRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\..\.."))
}
else { $WorkspaceRoot = [IO.Path]::GetFullPath($WorkspaceRoot) }
$tag = "v$Version"
$releaseDirectory = Join-Path $WorkspaceRoot "artifacts\desktop-release\$Version"
$installerName = "Oxo-Tracker_${Version}_x64-setup.exe"
$assetNames = @(
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

& (Join-Path $PSScriptRoot "Test-OxoRelease.ps1") -Version $Version -WorkspaceRoot $WorkspaceRoot
if ($LASTEXITCODE -ne 0) { throw "Local release validation failed." }
$buildInfo = Get-Content -LiteralPath (Join-Path $releaseDirectory "BUILD-INFO.json") -Raw -Encoding UTF8 | ConvertFrom-Json
if (!$buildInfo.updater_signature_verified) { throw "BUILD-INFO.json does not record an independently verified updater signature." }

function Get-GitHubToken {
    $git = (Get-Command git -ErrorAction Stop).Source
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = [Diagnostics.ProcessStartInfo]::new()
    $process.StartInfo.FileName = $git
    $process.StartInfo.Arguments = "credential-manager get --no-ui"
    $process.StartInfo.UseShellExecute = $false
    $process.StartInfo.RedirectStandardInput = $true
    $process.StartInfo.RedirectStandardOutput = $true
    $process.StartInfo.RedirectStandardError = $true
    $process.StartInfo.CreateNoWindow = $true
    [void]$process.Start()
    $process.StandardInput.WriteLine("protocol=https")
    $process.StandardInput.WriteLine("host=github.com")
    $process.StandardInput.WriteLine("")
    $process.StandardInput.Close()
    $output = $process.StandardOutput.ReadToEnd()
    $errorText = $process.StandardError.ReadToEnd()
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) { throw "Git Credential Manager failed: $errorText" }
    foreach ($line in ($output -split "\r?\n")) {
        if ($line.StartsWith("password=")) { return $line.Substring("password=".Length) }
    }
    throw "Git Credential Manager did not return a GitHub credential."
}

$token = $null
$headers = $null
try {
    $token = Get-GitHubToken
    $headers = @{
        Authorization = "Bearer $token"
        Accept = "application/vnd.github+json"
        "X-GitHub-Api-Version" = "2022-11-28"
        "User-Agent" = "Oxo-Release-Builder"
    }
    $apiRoot = "https://api.github.com/repos/$Repository"
    $response = Invoke-RestMethod -Uri "$apiRoot/releases?per_page=100" -Headers $headers -TimeoutSec 60
    $allReleases = @()
    for ($index = 0; $index -lt $response.Count; $index++) { $allReleases += $response[$index] }
    $matches = @($allReleases | Where-Object tag_name -eq $tag)
    if ($matches.Count -gt 1) { throw "Multiple GitHub releases exist for $tag; resolve them manually." }
    $release = if ($matches.Count -eq 1) { $matches[0] } else { $null }

    if ($release -and !$release.draft) {
        $remoteAssets = @($release.assets)
        $bad = @($assetNames | Where-Object {
            $name = $_
            $local = Get-Item -LiteralPath (Join-Path $releaseDirectory $name)
            $remote = @($remoteAssets | Where-Object name -eq $name)
            $remote.Count -ne 1 -or $remote[0].state -ne "uploaded" -or [long]$remote[0].size -ne $local.Length
        })
        $unexpected = @($remoteAssets | Where-Object { $_.name -notin $assetNames })
        if ($bad.Count -gt 0 -or $unexpected.Count -gt 0) {
            throw "Published release $tag differs from local artifacts. Never mutate or overwrite a published version; choose a new version."
        }
        [pscustomobject]@{ status = "already-published"; tag = $tag; url = $release.html_url; assets = $remoteAssets.Count } | ConvertTo-Json
        return
    }

    $notes = (Get-Content -LiteralPath (Join-Path $releaseDirectory "RELEASE-NOTES.md") -Raw -Encoding UTF8).Trim()
    $shortCommit = ([string]$buildInfo.source_commit).Substring(0, 7)
    $body = $notes + "`n`nSource commit: [$shortCommit](https://github.com/Oxo-AI-Security/Oxo-Tracker/commit/$($buildInfo.source_commit))  `nInstaller SHA-256: $($buildInfo.installer_sha256)"
    $metadata = @{
        tag_name = $tag
        target_commitish = "main"
        name = "Oxo Tracker v$Version (Preview)"
        body = $body
        draft = $true
        prerelease = $true
        generate_release_notes = $false
    }
    if (!$release) {
        $release = Invoke-RestMethod -Uri "$apiRoot/releases" -Method Post -Headers $headers -Body ($metadata | ConvertTo-Json -Depth 10) -ContentType "application/json" -TimeoutSec 60
    }
    else {
        $release = Invoke-RestMethod -Uri "$apiRoot/releases/$($release.id)" -Method Patch -Headers $headers -Body ($metadata | ConvertTo-Json -Depth 10) -ContentType "application/json" -TimeoutSec 60
    }

    $uploadRoot = $release.upload_url -replace '\{\?name,label\}$', ''
    foreach ($assetName in $assetNames) {
        $file = Get-Item -LiteralPath (Join-Path $releaseDirectory $assetName)
        $existing = @($release.assets | Where-Object name -eq $assetName)
        if ($existing.Count -gt 1) { throw "Draft contains duplicate asset name: $assetName" }
        if ($existing.Count -eq 1 -and $existing[0].state -eq "uploaded" -and [long]$existing[0].size -eq $file.Length) {
            Write-Host "Keeping complete draft asset: $assetName"
            continue
        }
        if ($existing.Count -eq 1) {
            Invoke-RestMethod -Uri "$apiRoot/releases/assets/$($existing[0].id)" -Method Delete -Headers $headers -TimeoutSec 60 | Out-Null
        }
        Write-Host "Uploading $assetName ($($file.Length) bytes)"
        $encodedName = [Uri]::EscapeDataString($assetName)
        $uploaded = Invoke-RestMethod -Uri "${uploadRoot}?name=$encodedName" -Method Post -Headers $headers -InFile $file.FullName -ContentType "application/octet-stream" -TimeoutSec 1800
        if ($uploaded.state -ne "uploaded" -or [long]$uploaded.size -ne $file.Length) { throw "GitHub rejected or truncated $assetName." }
        $release = Invoke-RestMethod -Uri "$apiRoot/releases/$($release.id)" -Headers $headers -TimeoutSec 60
    }

    $release = Invoke-RestMethod -Uri "$apiRoot/releases/$($release.id)" -Headers $headers -TimeoutSec 60
    $remoteAssets = @($release.assets)
    $invalid = @($assetNames | Where-Object {
        $name = $_
        $local = Get-Item -LiteralPath (Join-Path $releaseDirectory $name)
        $remote = @($remoteAssets | Where-Object name -eq $name)
        $remote.Count -ne 1 -or $remote[0].state -ne "uploaded" -or [long]$remote[0].size -ne $local.Length
    })
    $unexpected = @($remoteAssets | Where-Object { $_.name -notin $assetNames })
    if ($invalid.Count -gt 0 -or $unexpected.Count -gt 0 -or $remoteAssets.Count -ne $assetNames.Count) {
        throw "Draft asset gate failed. Invalid: $($invalid -join ', '); unexpected: $($unexpected.name -join ', ')"
    }

    $metadata.draft = $false
    $metadata.make_latest = "false"
    $release = Invoke-RestMethod -Uri "$apiRoot/releases/$($release.id)" -Method Patch -Headers $headers -Body ($metadata | ConvertTo-Json -Depth 10) -ContentType "application/json" -TimeoutSec 60
    if ($release.draft -or !$release.prerelease) { throw "GitHub did not publish the release as a pre-release." }
    $public = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repository/releases/tags/$tag" -Headers @{ "User-Agent" = "Oxo-Release-Builder" } -TimeoutSec 60
    if ($public.draft -or @($public.assets).Count -ne $assetNames.Count) { throw "Public GitHub release verification failed." }
    [pscustomobject]@{ status = "published"; tag = $tag; url = $release.html_url; assets = @($release.assets).Count } | ConvertTo-Json
}
finally {
    $token = $null
    if ($headers) { $headers.Authorization = $null }
}
