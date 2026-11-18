@echo off
setlocal enabledelayedexpansion
pushd "%~dp0"

REM ================================================================
REM  Build History Viewer
REM  Shows the audit log of previous build runs, including version,
REM  outcome, duration, and package size.
REM
REM  Usage:  11_build_history.bat [-n N] [--stats] [--clear [-y]]
REM    -n N      show last N entries (default: 10)
REM    --stats   show aggregate statistics
REM    --clear   clear history (prompts for confirmation)
REM    -y        skip confirmation when used with --clear
REM ================================================================

echo.
echo [BUILD HISTORY] %DATE% %TIME%
echo.

call "..\config\builder\builder_env.bat"
if errorlevel 1 ( echo [ERROR] Failed to load build environment. & popd & exit /b 1 )

call "%PYTHON%" "..\..\tools\build\scripts\build_history.py" %*
if errorlevel 1 ( echo. & echo [ERROR] Build history command failed. & popd & exit /b 1 )

popd
if not defined CI if not defined BATCH_NO_PAUSE pause
exit /b 0
