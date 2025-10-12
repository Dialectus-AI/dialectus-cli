@echo off
REM build-engine.bat
REM Build dialectus-engine wheel and install it into the CLI venv

setlocal enabledelayedexpansion

echo ==================================================
echo   Dialectus CLI - Engine Build Script
echo ==================================================
echo.

REM Paths
set "CLI_DIR=%~dp0"
set "ENGINE_DIR=%CLI_DIR%..\dialectus-engine"
set "DEPS_DIR=%CLI_DIR%deps"

REM Step 1: Verify dialectus-engine exists
echo [STEP] Verifying dialectus-engine directory...
if not exist "%ENGINE_DIR%" (
    echo [ERROR] dialectus-engine directory not found at: %ENGINE_DIR%
    exit /b 1
)
echo [OK] Found dialectus-engine at: %ENGINE_DIR%
echo.

REM Step 2: Build the wheel
echo [STEP] Building dialectus-engine wheel...
pushd "%ENGINE_DIR%"

REM Clean old builds
if exist "build" (
    rmdir /s /q "build"
    echo [OK] Cleaned: build
)
if exist "dist" (
    rmdir /s /q "dist"
    echo [OK] Cleaned: dist
)
for /d %%i in (*.egg-info) do (
    rmdir /s /q "%%i"
    echo [OK] Cleaned: %%i
)

REM Build wheel
python -m build --wheel
if errorlevel 1 (
    echo [ERROR] Wheel build failed
    popd
    exit /b 1
)
echo [OK] Wheel built successfully
echo.

popd

REM Step 3: Find the latest wheel
echo [STEP] Locating wheel file...
set "WHEEL_FILE="
for /f "delims=" %%i in ('dir /b /o-d "%ENGINE_DIR%\dist\*.whl" 2^>nul') do (
    set "WHEEL_FILE=%%i"
    goto :found_wheel
)
:found_wheel
if "%WHEEL_FILE%"=="" (
    echo [ERROR] No wheel file found in dist/
    exit /b 1
)
echo [OK] Found wheel: %WHEEL_FILE%
echo.

REM Step 4: Create deps directory if needed
if not exist "%DEPS_DIR%" (
    mkdir "%DEPS_DIR%"
    echo [OK] Created deps directory
)

REM Step 5: Copy wheel to deps
echo [STEP] Copying wheel to deps/...
copy /y "%ENGINE_DIR%\dist\%WHEEL_FILE%" "%DEPS_DIR%\" >nul
echo [OK] Copied to: %DEPS_DIR%\%WHEEL_FILE%
echo.

REM Step 6: Install the wheel
echo [STEP] Installing wheel with pip (into venv)...
pushd "%CLI_DIR%"
call venv\Scripts\pip.exe install --force-reinstall "%DEPS_DIR%\%WHEEL_FILE%"
if errorlevel 1 (
    echo [ERROR] Pip install failed
    popd
    exit /b 1
)
echo [OK] Wheel installed successfully into venv
echo.
popd

echo ==================================================
echo   Build Complete!
echo ==================================================
echo You can now run: python cli.py --help
echo.
