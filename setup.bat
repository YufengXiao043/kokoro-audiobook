@echo off
setlocal EnableDelayedExpansion

:: Always run from the project root (where this script lives)
cd /d "%~dp0"

echo ============================================================
echo  Kokoro Audiobook Pipeline - First-time Setup
echo ============================================================
echo.

:: ── Step 1: Check / install uv ──────────────────────────────────────
where uv >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [1/4] uv not found. Installing uv...
    powershell -NoProfile -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    :: Refresh PATH with known uv install locations for this session
    for %%L in ("%USERPROFILE%\.local\bin" "%LOCALAPPDATA%\uv\bin") do (
        if exist "%%~L\uv.exe" set "PATH=%%~L;!PATH!"
    )
    :: Verify uv is now reachable
    where uv >nul 2>&1
    if !ERRORLEVEL! NEQ 0 (
        echo.
        echo ERROR: uv was installed but cannot be found in PATH.
        echo Please close this window, open a new terminal, and re-run setup.bat.
        pause
        exit /b 1
    )
    echo uv installed successfully.
) else (
    echo [1/4] uv found: OK
)

echo.

:: ── Step 2: Install Python 3.11 + all Python dependencies ───────────
echo [2/4] Installing Python 3.11 and all dependencies via uv sync...
echo       (First run downloads ~1.5 GB including PyTorch CPU. Please wait.)
echo.
uv sync
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: uv sync failed. Common causes:
    echo   - No internet connection
    echo   - Insufficient disk space (need ~2 GB free)
    echo   - Antivirus blocking download or .venv creation
    echo.
    echo See the error output above for details.
    pause
    exit /b 1
)
echo Dependencies installed successfully.

echo.

:: ── Step 3: Check espeak-ng ──────────────────────────────────────────
echo [3/4] Checking espeak-ng (required for TTS)...
where espeak-ng >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo WARNING: espeak-ng NOT found in PATH.
    echo.
    echo espeak-ng is required for audio generation. To install:
    echo   1. Download the .msi installer:
    echo      https://github.com/espeak-ng/espeak-ng/releases
    echo      ^(pick: espeak-ng-XXXXXXXXX-x64.msi^)
    echo   2. Run the installer. It adds espeak-ng to your PATH automatically.
    echo   3. Open a NEW terminal and re-run this script to confirm.
    echo.
    echo Audio generation will fail until espeak-ng is installed.
    echo.
) else (
    echo espeak-ng found: OK
)

:: ── Step 4: Pre-download Kokoro model weights ────────────────────────
echo [4/4] Pre-downloading Kokoro model weights...
echo       (Downloads ~330 MB on first run, cached for offline use.)
uv run python -c "from kokoro import KPipeline; KPipeline(lang_code='a')"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo WARNING: Could not pre-download model weights.
    echo   - If espeak-ng is missing, install it first, then re-run this script.
    echo   - Otherwise, weights will download automatically on first use.
) else (
    echo Model weights cached: OK
)

echo.
echo ============================================================
echo  Setup complete!
echo.
echo  QUICK START (one command does everything):
echo.
echo    From a URL:
echo      uv run python src\run.py "https://example.com/article"
echo.
echo    From a PDF:
echo      uv run python src\run.py input\mybook.pdf
echo.
echo    From a text file:
echo      uv run python src\run.py input\mybook.txt
echo.
echo  Each command extracts, generates audio, and opens the player.
echo  For all options and details: see README.md
echo ============================================================
echo.
pause
