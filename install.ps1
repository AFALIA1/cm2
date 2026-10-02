# cm2 installer for Windows (PowerShell 5.1+).
# Installs ffmpeg + Python 3.9+ via winget (if missing), creates .\venv, and installs cm2 into it.
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $ScriptDir "venv"

function Info($msg) { Write-Host "==> $msg" }
function Die($msg) { Write-Host "ERROR: $msg" -ForegroundColor Red; exit 1 }
function Have($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

# winget installs update PATH in the registry, not in this session - reload it.
function Refresh-Path {
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
}

function Winget-Install($id) {
    if (-not (Have "winget")) {
        Die "winget not found. Install '$id' manually (or install App Installer from the Microsoft Store), then re-run."
    }
    Info "Installing $id via winget..."
    winget install --id $id -e --accept-source-agreements --accept-package-agreements
    Refresh-Path
}

# Returns the command for a Python >= 3.9, or $null. Skips the Microsoft Store stub.
function Find-Python {
    foreach ($candidate in @("py -3", "python", "python3")) {
        $parts = $candidate.Split(" ")
        $exe = $parts[0]
        if (-not (Have $exe)) { continue }
        $checkArgs = @($parts | Select-Object -Skip 1) + @("-c", "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)")
        try {
            & $exe @checkArgs 2>$null
            if ($LASTEXITCODE -eq 0) { return $candidate }
        } catch { }
    }
    return $null
}

if (-not (Have "ffmpeg") -or -not (Have "ffprobe")) {
    Winget-Install "Gyan.FFmpeg"
}
if (-not (Have "ffmpeg")) { Die "ffmpeg not found on PATH after install. Open a new terminal and re-run." }
if (-not (Have "ffprobe")) { Die "ffprobe not found on PATH after install. Open a new terminal and re-run." }

$Python = Find-Python
if (-not $Python) {
    Winget-Install "Python.Python.3.12"
    $Python = Find-Python
}
if (-not $Python) { Die "Python 3.9 or newer is required. Open a new terminal and re-run." }

$pyParts = $Python.Split(" ")
$pyExe = $pyParts[0]
$pyArgs = @($pyParts | Select-Object -Skip 1)
Info ("Using " + (& $pyExe @pyArgs --version))

Info "Creating Python virtual environment in $VenvDir..."
& $pyExe @pyArgs -m venv $VenvDir
if ($LASTEXITCODE -ne 0) { Die "Failed to create virtual environment." }

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { Die "Failed to upgrade pip." }
& $VenvPython -m pip install -e $ScriptDir
if ($LASTEXITCODE -ne 0) { Die "Failed to install cm2." }

Write-Host ""
Write-Host "Setup complete. Activate with:"
Write-Host "  PowerShell:  $VenvDir\Scripts\Activate.ps1"
Write-Host "  cmd.exe:     $VenvDir\Scripts\activate.bat"
Write-Host "Then run: cm2"
