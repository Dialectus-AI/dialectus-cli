# build-engine.ps1
# Build dialectus-engine wheel and install it into the CLI venv

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Step { param($msg) Write-Host "`n[STEP] $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Error { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor Red }

# Paths
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$cliDir = $scriptDir
$engineDir = Join-Path (Split-Path -Parent $cliDir) "dialectus-engine"
$depsDir = Join-Path $cliDir "deps"

Write-Host "==================================================" -ForegroundColor Yellow
Write-Host "  Dialectus CLI - Engine Build Script" -ForegroundColor Yellow
Write-Host "==================================================" -ForegroundColor Yellow

# Step 1: Verify dialectus-engine exists
Write-Step "Verifying dialectus-engine directory..."
if (-not (Test-Path $engineDir)) {
    Write-Error "dialectus-engine directory not found at: $engineDir"
    exit 1
}
Write-Success "Found dialectus-engine at: $engineDir"

# Step 2: Build the wheel
Write-Step "Building dialectus-engine wheel..."
Push-Location $engineDir
try {
    # Clean old builds
    @("build", "dist", "*.egg-info") | ForEach-Object {
        $pattern = $_
        Get-ChildItem -Path . -Filter $pattern -ErrorAction SilentlyContinue | ForEach-Object {
            Remove-Item -Recurse -Force $_.FullName
            Write-Success "Cleaned: $($_.Name)"
        }
    }

    # Build wheel
    python -m build --wheel
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Wheel build failed"
        exit 1
    }
    Write-Success "Wheel built successfully"
} finally {
    Pop-Location
}

# Step 3: Find the latest wheel
Write-Step "Locating wheel file..."
$wheelFiles = Get-ChildItem -Path (Join-Path $engineDir "dist") -Filter "*.whl" | Sort-Object LastWriteTime -Descending
if ($wheelFiles.Count -eq 0) {
    Write-Error "No wheel file found in dist/"
    exit 1
}
$latestWheel = $wheelFiles[0]
Write-Success "Found wheel: $($latestWheel.Name)"

# Step 4: Create deps directory if needed
if (-not (Test-Path $depsDir)) {
    New-Item -ItemType Directory -Path $depsDir | Out-Null
    Write-Success "Created deps directory"
}

# Step 5: Copy wheel to deps
Write-Step "Copying wheel to deps/..."
$destPath = Join-Path $depsDir $latestWheel.Name
Copy-Item -Path $latestWheel.FullName -Destination $destPath -Force
Write-Success "Copied to: $destPath"

# Step 6: Install the wheel
Write-Step "Installing wheel with pip (into venv)..."
Push-Location $cliDir
try {
    .\venv\Scripts\pip.exe install --force-reinstall $destPath
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Pip install failed"
        exit 1
    }
    Write-Success "Wheel installed successfully into venv"
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "==================================================" -ForegroundColor Green
Write-Host "  Build Complete!" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
Write-Host "You can now run: " -NoNewline
Write-Host "python cli.py --help" -ForegroundColor Cyan
Write-Host ""
