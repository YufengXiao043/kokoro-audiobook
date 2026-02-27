@echo off
setlocal EnableDelayedExpansion

echo ============================================================
echo  Kokoro Audiobook Pipeline - First-time Setup
echo ============================================================
echo.

:: ── Check / install uv ───────────────────────────────────────────────
where uv >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [1/4] uv not found. Installing uv...
    powershell -NoProfile -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Failed to install uv. Please install manually:
        echo   https://docs.astral.sh/uv/getting-started/installation/
        pause
        exit /b 1
    )
    :: Refresh PATH so uv is available in this session
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
    echo uv installed successfully.
) else (
    echo [1/4] uv found: OK
)

echo.

:: ── Install Python + dependencies via uv ────────────────────────────
echo [2/4] Installing Python 3.11 and all dependencies via uv...
echo       (First run downloads ~1-2 GB including PyTorch CPU. Please wait.)
echo.
uv sync
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: uv sync failed. See errors above.
    pause
    exit /b 1
)
echo.
echo Dependencies installed successfully.

echo.

:: ── Check espeak-ng ──────────────────────────────────────────────────
echo [3/4] Checking espeak-ng...
where espeak-ng >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo WARNING: espeak-ng not found in PATH.
    echo.
    echo espeak-ng is REQUIRED for Kokoro TTS to generate audio.
    echo.
    echo Please install it:
    echo   1. Download the Windows installer from:
    echo      https://github.com/espeak-ng/espeak-ng/releases
    echo      ^(look for espeak-ng-XXXXX-x64.msi^)
    echo   2. Run the installer - it will add espeak-ng to your PATH
    echo   3. Restart this terminal and re-run setup.bat
    echo.
) else (
    echo espeak-ng found: OK
)

echo.

:: ── Pre-download Kokoro model weights ───────────────────────────────
echo [4/4] Pre-downloading Kokoro model weights...
echo       (Downloads ~330 MB on first run. Cached for offline use.)
uv run python -c "from kokoro import KPipeline; KPipeline(lang_code='a')" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Could not pre-download model weights.
    echo          They will be downloaded on first use of generate.py.
    echo          Make sure espeak-ng is installed first.
) else (
    echo Model weights downloaded and cached: OK
)

echo.
echo ============================================================
echo  Setup complete!
echo.
echo  Usage:
echo    Extract PDF:   uv run python src/extract.py input/mybook.pdf
echo    Extract URL:   uv run python src/extract.py "https://example.com/article"
echo    Generate:      uv run python src/generate.py input/mybook.txt
echo    Then open:     player\player.html  in your browser
echo ============================================================
echo.
pause
