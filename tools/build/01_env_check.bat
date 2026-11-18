@echo off
setlocal enabledelayedexpansion
pushd "%~dp0"

REM ================================================================
REM  Environment Check
REM  Verifies that all tools, executables, Python packages, and
REM  signing keys required for building are present and correct.
REM  Run this before building to catch configuration problems early.
REM ================================================================

echo.
echo [ENV CHECK] %DATE% %TIME%
echo.

call "..\config\builder\builder_env.bat"
if errorlevel 1 ( echo [ERROR] Failed to load build environment. & popd & exit /b 1 )

call "%PYTHON%" "..\..\tools\build\scripts\env_check.py"
if errorlevel 1 ( echo. & echo [ERROR] Environment check failed. & popd & exit /b 1 )

popd
if not defined CI if not defined BATCH_NO_PAUSE pause
exit /b 0
