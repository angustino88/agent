@echo off
setlocal enabledelayedexpansion
pushd "%~dp0"

:: ================================================================
::  Rebuild Software  (clean)
::  Clears all cached output and performs a full build from scratch.
:: ================================================================

echo.
echo [REBUILD] %DATE% %TIME%
echo.

call "..\config\builder\builder_env.bat"
if errorlevel 1 ( echo [ERROR] Failed to load build environment. & popd & exit /b 1 )

call "%PYTHON%" "..\..\tools\build\scripts\build.py" --rebuild
if errorlevel 1 ( echo. & echo [ERROR] Rebuild failed. & popd & exit /b 1 )

REM --- Build Chocolatey NuGet package
echo.
echo [INFO] Building NuGet package...
call "%PYTHON%" "..\..\tools\build\scripts\build_nuget.py"
if errorlevel 1 ( echo [WARN] NuGet packaging failed - software rebuild succeeded. )

echo.
echo [OK] Rebuild completed successfully.
popd
if not defined CI if not defined BATCH_NO_PAUSE pause
exit /b 0
