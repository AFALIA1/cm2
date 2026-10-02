# Builds dist\cm2-<version>-windows-x64-setup.exe on Windows (run packaging\build_app.py first).
# Bundles ffmpeg + ffprobe and wraps everything in one Inno Setup installer.
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$App = Join-Path $Root "dist\cm2"
$Dl = Join-Path $Root "build\win"
$Version = (Select-String -Path (Join-Path $Root "pyproject.toml") -Pattern '^version = "(.*)"').Matches[0].Groups[1].Value

if (-not (Test-Path (Join-Path $App "cm2.exe"))) { throw "dist\cm2\cm2.exe missing - run packaging\build_app.py first" }

New-Item -ItemType Directory -Force -Path $Dl | Out-Null
$Zip = Join-Path $Dl "ffmpeg.zip"
Invoke-WebRequest -Uri "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -OutFile $Zip
$Extract = Join-Path $Dl "ffmpeg"
if (Test-Path $Extract) { Remove-Item -Recurse -Force $Extract }
Expand-Archive -Path $Zip -DestinationPath $Extract
foreach ($tool in @("ffmpeg.exe", "ffprobe.exe")) {
    $src = Get-ChildItem -Path $Extract -Recurse -Filter $tool | Select-Object -First 1
    Copy-Item $src.FullName (Join-Path $App $tool) -Force
}

$Iscc = (Get-Command iscc -ErrorAction SilentlyContinue).Source
if (-not $Iscc) { $Iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" }
if (-not (Test-Path $Iscc)) { throw "Inno Setup 6 not found - install it from https://jrsoftware.org/isinfo.php" }

& $Iscc "/DAppVersion=$Version" (Join-Path $Root "packaging\cm2.iss")
if ($LASTEXITCODE -ne 0) { throw "ISCC failed" }
Write-Host "Built $Root\dist\cm2-$Version-windows-x64-setup.exe"
