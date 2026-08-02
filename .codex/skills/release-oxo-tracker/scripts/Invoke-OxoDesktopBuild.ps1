param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version,
    [string]$WorkspaceRoot,
    [string]$PrivateKeyPath,
    [securestring]$SigningPassword,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $WorkspaceRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\..\.."))
}
else {
    $WorkspaceRoot = [IO.Path]::GetFullPath($WorkspaceRoot)
}
if ([string]::IsNullOrWhiteSpace($PrivateKeyPath)) {
    $PrivateKeyPath = Join-Path $env:USERPROFILE ".tauri\oxo-tracker.key"
}
$PrivateKeyPath = [IO.Path]::GetFullPath($PrivateKeyPath)
$publicKeyPath = Join-Path $WorkspaceRoot "frontend\src-tauri\updater.pubkey"
$buildScript = Join-Path $WorkspaceRoot "scripts\build-desktop.ps1"

if (!(Test-Path -LiteralPath $PrivateKeyPath -PathType Leaf)) { throw "Updater private key not found: $PrivateKeyPath" }
if (!(Test-Path -LiteralPath $publicKeyPath -PathType Leaf)) { throw "Updater public key not found: $publicKeyPath" }
if (!(Test-Path -LiteralPath $buildScript -PathType Leaf)) { throw "Canonical desktop build script not found: $buildScript" }

$origin = (& git -C $WorkspaceRoot remote get-url origin).Trim()
if ($LASTEXITCODE -ne 0 -or $origin -notmatch 'Oxo-AI-Security/Oxo-Tracker(?:\.git)?$') {
    throw "Workspace origin is not Oxo-AI-Security/Oxo-Tracker: $origin"
}
$status = @(& git -C $WorkspaceRoot status --porcelain)
if ($LASTEXITCODE -ne 0) { throw "Unable to inspect the source worktree." }
if ($status.Count -gt 0) { throw "Desktop releases require a clean source worktree. Commit the intended changes first." }

function Read-UpdaterPassword {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    $form = [Windows.Forms.Form]::new()
    $form.Text = "Oxo Tracker updater signing"
    $form.Width = 480
    $form.Height = 175
    $form.StartPosition = "CenterScreen"
    $form.TopMost = $true
    $label = [Windows.Forms.Label]::new()
    $label.Text = "Enter the password for oxo-tracker.key:"
    $label.AutoSize = $true
    $label.Left = 18
    $label.Top = 18
    $box = [Windows.Forms.TextBox]::new()
    $box.Left = 18
    $box.Top = 45
    $box.Width = 425
    $box.UseSystemPasswordChar = $true
    $ok = [Windows.Forms.Button]::new()
    $ok.Text = "Sign build"
    $ok.Left = 266
    $ok.Top = 80
    $ok.DialogResult = [Windows.Forms.DialogResult]::OK
    $cancel = [Windows.Forms.Button]::new()
    $cancel.Text = "Cancel"
    $cancel.Left = 365
    $cancel.Top = 80
    $cancel.DialogResult = [Windows.Forms.DialogResult]::Cancel
    $form.Controls.AddRange(@($label, $box, $ok, $cancel))
    $form.AcceptButton = $ok
    $form.CancelButton = $cancel
    $form.Add_Shown({ $box.Focus() })
    if ($form.ShowDialog() -ne [Windows.Forms.DialogResult]::OK -or [string]::IsNullOrEmpty($box.Text)) {
        $form.Dispose()
        throw "Updater signing was cancelled."
    }
    $secure = ConvertTo-SecureString $box.Text -AsPlainText -Force
    $box.Clear()
    $form.Dispose()
    return $secure
}

if (!$SigningPassword) { $SigningPassword = Read-UpdaterPassword }
$previousKeyPath = $env:TAURI_SIGNING_PRIVATE_KEY_PATH
$previousPassword = $env:TAURI_SIGNING_PRIVATE_KEY_PASSWORD
$passwordPointer = [IntPtr]::Zero
try {
    $passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SigningPassword)
    $env:TAURI_SIGNING_PRIVATE_KEY_PATH = $PrivateKeyPath
    $env:TAURI_SIGNING_PRIVATE_KEY_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer)
    $arguments = @{
        Version = $Version
        UpdaterPublicKey = $publicKeyPath
        UpdaterEndpoint = "https://oxotracker.oss-cn-beijing.aliyuncs.com/stable/latest.json"
        AllowUnsigned = $true
        SkipTests = $SkipTests
    }
    & $buildScript @arguments
    if ($LASTEXITCODE -ne 0) { throw "Desktop build failed with exit code $LASTEXITCODE." }
    & (Join-Path $PSScriptRoot "New-OxoReleaseMetadata.ps1") -Version $Version -WorkspaceRoot $WorkspaceRoot
    if ($LASTEXITCODE -ne 0) { throw "Release metadata generation failed with exit code $LASTEXITCODE." }
    & (Join-Path $PSScriptRoot "Test-OxoRelease.ps1") -Version $Version -WorkspaceRoot $WorkspaceRoot -MarkVerified
    if ($LASTEXITCODE -ne 0) { throw "Release validation failed with exit code $LASTEXITCODE." }
}
finally {
    if ($passwordPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer)
    }
    $env:TAURI_SIGNING_PRIVATE_KEY_PATH = $previousKeyPath
    $env:TAURI_SIGNING_PRIVATE_KEY_PASSWORD = $previousPassword
    $SigningPassword = $null
}
