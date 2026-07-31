function Initialize-OxoDesktopToolchain {
    param(
        [Parameter(Mandatory = $true)]
        [string]$WorkspaceRoot
    )

    $workspace = [IO.Path]::GetFullPath($WorkspaceRoot)
    $buildRoot = Join-Path $workspace ".desktop-build"
    $cargoBin = Join-Path $env:USERPROFILE ".cargo\bin"
    $llvmBin = Join-Path $buildRoot "tooling\llvm\bin"
    if (Test-Path -LiteralPath $cargoBin) { $env:PATH = "$cargoBin;$env:PATH" }
    if (Test-Path -LiteralPath $llvmBin) { $env:PATH = "$llvmBin;$env:PATH" }

    foreach ($tool in @("cargo", "rustup")) {
        if (!(Get-Command $tool -ErrorAction SilentlyContinue)) {
            throw "$tool is required for desktop development. Install the Rust toolchain with rustup."
        }
    }

    $usePortableMsvc = !(Get-Command "link.exe" -ErrorAction SilentlyContinue)
    if (!$usePortableMsvc) { return $false }

    $xwinRoot = Join-Path $env:LOCALAPPDATA "cargo-xwin\xwin"
    $requiredSdkFiles = @(
        (Join-Path $xwinRoot "crt\lib\x86_64\libcmt.lib"),
        (Join-Path $xwinRoot "sdk\lib\ucrt\x86_64\ucrt.lib"),
        (Join-Path $xwinRoot "sdk\lib\um\x86_64\kernel32.lib")
    )
    if (@($requiredSdkFiles | Where-Object { !(Test-Path -LiteralPath $_) }).Count -gt 0) {
        if (!(Get-Command "cargo-xwin" -ErrorAction SilentlyContinue)) {
            throw "Visual Studio Build Tools were not found and the portable Windows SDK cache is missing. Install Visual Studio Build Tools with the Desktop development with C++ workload, or install cargo-xwin plus LLVM/LLD."
        }
        & cargo-xwin xwin cache xwin
        if ($LASTEXITCODE -ne 0) { throw "cargo-xwin failed to populate the Windows SDK cache" }
    }
    if (@($requiredSdkFiles | Where-Object { !(Test-Path -LiteralPath $_) }).Count -gt 0) {
        throw "cargo-xwin did not create a complete Windows SDK cache at $xwinRoot"
    }
    foreach ($tool in @("clang-cl", "lld-link", "llvm-lib", "llvm-rc")) {
        if (!(Get-Command $tool -ErrorAction SilentlyContinue)) {
            throw "$tool is required when Visual Studio Build Tools are unavailable"
        }
    }

    $env:INCLUDE = @(
        (Join-Path $xwinRoot "crt\include"),
        (Join-Path $xwinRoot "sdk\include\ucrt"),
        (Join-Path $xwinRoot "sdk\include\shared"),
        (Join-Path $xwinRoot "sdk\include\um"),
        (Join-Path $xwinRoot "sdk\include\winrt"),
        (Join-Path $xwinRoot "sdk\include\cppwinrt")
    ) -join ";"
    $env:LIB = @(
        (Join-Path $xwinRoot "crt\lib\x86_64"),
        (Join-Path $xwinRoot "sdk\lib\ucrt\x86_64"),
        (Join-Path $xwinRoot "sdk\lib\um\x86_64")
    ) -join ";"
    $env:CC_x86_64_pc_windows_msvc = "clang-cl"
    $env:CXX_x86_64_pc_windows_msvc = "clang-cl"
    $env:AR_x86_64_pc_windows_msvc = "llvm-lib"
    $env:RC_x86_64_pc_windows_msvc = "llvm-rc"
    $env:RC = "llvm-rc"
    $env:CARGO_TARGET_X86_64_PC_WINDOWS_MSVC_LINKER = "lld-link"

    $installedTargets = @(& rustup target list --installed)
    if ($LASTEXITCODE -ne 0) { throw "rustup target list failed" }
    if ("x86_64-pc-windows-msvc" -notin $installedTargets) {
        & rustup target add x86_64-pc-windows-msvc
        if ($LASTEXITCODE -ne 0) { throw "rustup target add x86_64-pc-windows-msvc failed" }
    }
    return $true
}
