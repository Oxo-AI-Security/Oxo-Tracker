param(
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version,
    [string]$Repository = "Oxo-AI-Security/Oxo-Tracker-Releases"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$response = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repository/releases?per_page=100" `
    -Headers @{ "User-Agent" = "Oxo-Release-Builder"; Accept = "application/vnd.github+json" } `
    -TimeoutSec 60
$releases = @()
for ($index = 0; $index -lt $response.Count; $index++) { $releases += $response[$index] }
$semanticReleases = @($releases | Where-Object { $_.tag_name -match '^v(\d+\.\d+\.\d+)$' })
$versions = @($semanticReleases | ForEach-Object { [version]$_.tag_name.Substring(1) } | Sort-Object -Descending)
$latest = if ($versions.Count -gt 0) { $versions[0] } else { [version]"0.0.0" }
$target = if ($Version) { [version]$Version } else { [version]::new($latest.Major, $latest.Minor, $latest.Build + 1) }
$matching = @($semanticReleases | Where-Object { $_.tag_name -eq "v$target" } | Select-Object -First 1)

[pscustomobject]@{
    latest_version = $latest.ToString(3)
    target_version = $target.ToString(3)
    tag = "v$target"
    exists = $matching.Count -gt 0
    published = $matching.Count -gt 0 -and !$matching[0].draft
    release_url = if ($matching.Count -gt 0) { $matching[0].html_url } else { $null }
} | ConvertTo-Json -Depth 4
