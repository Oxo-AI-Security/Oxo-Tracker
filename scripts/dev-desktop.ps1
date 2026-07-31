param()

$ErrorActionPreference = "Stop"
$WorkspaceRoot = [IO.Path]::GetFullPath((Split-Path $PSScriptRoot -Parent))
$FrontendRoot = Join-Path $WorkspaceRoot "frontend"
$TauriRoot = Join-Path $FrontendRoot "src-tauri"
$Python = Join-Path $WorkspaceRoot ".venv\Scripts\python.exe"
$MoonshotRoot = Join-Path $WorkspaceRoot "data\moonshot-data"
$ResourceRoot = Join-Path $TauriRoot "resources"
$AppHome = Join-Path $env:LOCALAPPDATA "com.oxoai.oxo-tracker-development"
. (Join-Path $PSScriptRoot "desktop-toolchain.ps1")

if (!(Test-Path -LiteralPath $Python)) {
    throw "Python development environment was not found at $Python. Run scripts\bootstrap.ps1 first."
}
if (!(Test-Path -LiteralPath (Join-Path $MoonshotRoot "datasets"))) {
    throw "Moonshot development assets were not found at $MoonshotRoot. Install them before starting the desktop app."
}
if (!(Test-Path -LiteralPath (Join-Path $FrontendRoot "node_modules"))) {
    throw "Frontend dependencies are missing. Run npm install in $FrontendRoot first."
}
if (!(Get-Command "npm" -ErrorAction SilentlyContinue)) {
    throw "npm is required for desktop development but was not found on PATH"
}

$devServerPort = 5173
$portListeners = @(Get-NetTCPConnection -LocalPort $devServerPort -State Listen -ErrorAction SilentlyContinue)
if ($portListeners.Count -gt 0) {
    $ownerDescriptions = foreach ($processId in ($portListeners.OwningProcess | Sort-Object -Unique)) {
        $owner = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($owner) { "$($owner.ProcessName) (PID $processId)" } else { "PID $processId" }
    }
    throw "Desktop development port $devServerPort is already in use by $($ownerDescriptions -join ', '). Stop that process and run this command again."
}

$UsePortableMsvc = Initialize-OxoDesktopToolchain -WorkspaceRoot $WorkspaceRoot
New-Item -ItemType Directory -Path $AppHome -Force | Out-Null

$token = [guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")
$backendArguments = @(
    "-m", "app.desktop_server",
    "--token", $token,
    "--resource-root", $ResourceRoot,
    "--app-home", $AppHome,
    "--asset-version", "development",
    "--development",
    "--moonshot-data-root", $MoonshotRoot
)
$startInfo = [Diagnostics.ProcessStartInfo]::new()
$startInfo.FileName = $Python
$startInfo.WorkingDirectory = $WorkspaceRoot
$startInfo.UseShellExecute = $false
$startInfo.CreateNoWindow = $true
$startInfo.RedirectStandardOutput = $true
$startInfo.RedirectStandardError = $true
$startInfo.Arguments = ($backendArguments | ForEach-Object {
    '"' + ([string]$_).Replace('"', '\"') + '"'
}) -join " "
$backend = [Diagnostics.Process]::new()
$backend.StartInfo = $startInfo

$environmentNames = @(
    "OXO_DESKTOP_DEV_API_BASE_URL",
    "OXO_DESKTOP_DEV_TOKEN",
    "OXO_DESKTOP_DEV_PORT"
)
$previousEnvironment = @{}
foreach ($name in $environmentNames) {
    $previousEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
}

try {
    [void]$backend.Start()
    $stderrTask = $backend.StandardError.ReadToEndAsync()
    $ready = $null
    $deadline = [DateTime]::UtcNow.AddSeconds(90)
    while ([DateTime]::UtcNow -lt $deadline -and !$ready) {
        $readTask = $backend.StandardOutput.ReadLineAsync()
        while (!$readTask.IsCompleted -and [DateTime]::UtcNow -lt $deadline) {
            if ($backend.HasExited) { break }
            Start-Sleep -Milliseconds 100
        }
        if (!$readTask.IsCompleted) { break }
        $line = $readTask.Result
        if ($null -eq $line) { break }
        if ($line.StartsWith("OXO_DESKTOP_READY ")) {
            $ready = $line.Substring("OXO_DESKTOP_READY ".Length) | ConvertFrom-Json
        }
    }
    if (!$ready) {
        if (!$backend.HasExited) { $backend.Kill() }
        [void]$stderrTask.Wait(3000)
        $backendError = if ($stderrTask.IsCompleted) { $stderrTask.Result } else { "" }
        throw "Desktop development backend did not become ready. $backendError"
    }
    if ($ready.host -ne "127.0.0.1") {
        throw "Desktop development backend did not bind to loopback"
    }

    $env:OXO_DESKTOP_DEV_API_BASE_URL = "http://127.0.0.1:$($ready.port)"
    $env:OXO_DESKTOP_DEV_TOKEN = $token
    $env:OXO_DESKTOP_DEV_PORT = [string]$ready.port
    $toolchainLabel = if ($UsePortableMsvc) { "portable LLVM/MSVC SDK" } else { "Visual Studio Build Tools" }
    Write-Host "Oxo Tracker development backend is ready at $($env:OXO_DESKTOP_DEV_API_BASE_URL)"
    Write-Host "Starting Tauri development window with $toolchainLabel (no PyInstaller or NSIS packaging)."

    Push-Location $FrontendRoot
    try {
        & npm run tauri -- dev --config src-tauri/tauri.dev.conf.json
        if ($LASTEXITCODE -ne 0) { throw "Tauri development process failed with exit code $LASTEXITCODE" }
    }
    finally {
        Pop-Location
    }
}
finally {
    foreach ($name in $environmentNames) {
        $previous = $previousEnvironment[$name]
        if ($null -eq $previous) {
            Remove-Item "Env:$name" -ErrorAction SilentlyContinue
        }
        else {
            [Environment]::SetEnvironmentVariable($name, $previous, "Process")
        }
    }
    if ($backend -and !$backend.HasExited) { $backend.Kill() }
    if ($backend) { $backend.Dispose() }
}
