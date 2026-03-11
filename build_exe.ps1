$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$python = Join-Path $projectRoot "venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Expected virtualenv Python at '$python'."
}

Write-Host "Using Python:" $python

& $python -m pip install pyinstaller
& $python -m PyInstaller --noconfirm --clean "SundPood.spec"

$distDir = Join-Path $projectRoot "dist\SundPood"
$soundsDir = Join-Path $distDir "sounds"
$settingsPath = Join-Path $distDir "settings.json"

if (-not (Test-Path $soundsDir)) {
    New-Item -ItemType Directory -Path $soundsDir | Out-Null
}

if (Test-Path $settingsPath) {
    Remove-Item $settingsPath -Force
}

Write-Host ""
Write-Host "Build complete."
Write-Host "Portable app folder:" $distDir
Write-Host "Executable:" (Join-Path $distDir "SundPood.exe")
