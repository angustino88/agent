@echo off
setlocal enabledelayedexpansion
pushd "%~dp0"

:: ================================================================
::  Clean All
::  Removes all build output directories: tmp, dist, log.
:: ================================================================

echo.
echo [CLEAN] %DATE% %TIME%
echo.

call "..\config\builder\builder_env.bat"
if errorlevel 1 ( echo [ERROR] Failed to load build environment. & popd & exit /b 1 )

call "%PYTHON%" "..\..\tools\build\scripts\build.py" --clean
if errorlevel 1 ( echo. & echo [ERROR] Clean failed. & popd & exit /b 1 )

echo.
echo [OK] Clean completed successfully.
popd
if not defined CI if not defined BATCH_NO_PAUSE pause
exit /b 0
