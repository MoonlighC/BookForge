$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Compiler = Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"
$InstallerScript = Join-Path $PSScriptRoot "BookForge.iss"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "BookForge virtual environment not found: $Python"
}
if (-not (Test-Path -LiteralPath $Compiler)) {
    throw "Inno Setup 6 was not found: $Compiler"
}
if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot "dist\BookForge\BookForge.exe"))) {
    throw "Build the portable PyInstaller distribution before the installer."
}

$env:BOOKFORGE_VERSION = & $Python -c "import bookforge; print(bookforge.__version__)"
if ($LASTEXITCODE -ne 0 -or -not $env:BOOKFORGE_VERSION) {
    throw "Could not read the centralized BookForge version."
}

Push-Location $ProjectRoot
try {
    & $Compiler $InstallerScript
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
