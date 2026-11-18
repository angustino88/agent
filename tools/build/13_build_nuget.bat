@echo off
setlocal enabledelayedexpansion
pushd "%~dp0"

REM ================================================================
REM  Build NuGet / Chocolatey Package
REM  Packs the application ZIP into a Chocolatey .nupkg using
REM  `choco pack`.  The nuspec version and release notes are synced
REM  automatically from VersionConfig / BuildConfig.
REM
REM  Prerequisites:
REM    - Software must have been built first (05_build.bat or
REM      06_rebuild.bat) so the ZIP artifact exists in prj/build/app/.
REM    - Chocolatey (choco.exe) must be installed and on PATH.
REM ================================================================

echo.
echo [NUGET] %DATE% %TIME%
echo.

call "..\..\prj\config\builder\builder_env.bat"
if errorlevel 1 ( echo [ERROR] Failed to load build environment. & popd & exit /b 1 )

call "%PYTHON%" "..\..\tools\build\scripts\build_nuget.py"
if errorlevel 1 ( echo. & echo [ERROR] NuGet package build failed. & popd & exit /b 1 )

echo.
echo [OK] NuGet package built successfully.
popd
if not defined CI if not defined BATCH_NO_PAUSE pause
exit /b 0
