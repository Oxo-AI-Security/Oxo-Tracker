param(
    [Parameter(Mandatory = $true)]
    [string]$StagedAssets,
    [Parameter(Mandatory = $true)]
    [string]$PolicyPath
)

$ErrorActionPreference = "Stop"
$stagedRoot = [IO.Path]::GetFullPath($StagedAssets).TrimEnd('\')
$policyFile = [IO.Path]::GetFullPath($PolicyPath)
if (!(Test-Path -LiteralPath $stagedRoot -PathType Container)) {
    throw "Staged Moonshot directory not found: $stagedRoot"
}
if (!(Test-Path -LiteralPath $policyFile -PathType Leaf)) {
    throw "Desktop asset policy not found: $policyFile"
}

$policy = Get-Content -LiteralPath $policyFile -Raw -Encoding UTF8 | ConvertFrom-Json
$relativePaths = @($policy.excludedAssets) + @($policy.excludedUserAssets)
foreach ($relative in $relativePaths) {
    if ([string]::IsNullOrWhiteSpace($relative) -or [IO.Path]::IsPathRooted($relative)) {
        throw "Excluded desktop asset must be a relative path: $relative"
    }
    $target = [IO.Path]::GetFullPath((Join-Path $stagedRoot $relative))
    if (!$target.StartsWith("$stagedRoot\", [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove an excluded asset outside the staged directory: $relative"
    }
    if (Test-Path -LiteralPath $target) {
        Remove-Item -LiteralPath $target -Force
    }
}

Write-Host "Applied $($relativePaths.Count) desktop asset exclusion rule(s)."
