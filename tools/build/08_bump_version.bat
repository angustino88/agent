@echo off
setlocal enabledelayedexpansion
pushd "%~dp0"

REM ================================================================
REM  Bump Version
REM  Interactively bumps APP_VERSION in version_config.py and
REM  collects CHANGELOG entries for the release.
REM
REM  Usage:  10_bump_version.bat [--patch|--minor|--major|X.Y.Z] [--no-commit]
REM    --patch       bump patch  (1.2.3 -> 1.2.4)
REM    --minor       bump minor  (1.2.3 -> 1.3.0)
REM    --major       bump major  (1.2.3 -> 2.0.0)
REM    X.Y.Z         set exact version
REM    --no-commit   skip the git commit prompt
REM ================================================================

echo.
echo [BUMP VERSION] %DATE% %TIME%
echo.

call "..\config\builder\builder_env.bat"
if errorlevel 1 ( echo [ERROR] Failed to load build environment. & popd & exit /b 1 )

call "%PYTHON%" "..\..\tools\build\scripts\bump_version.py" %*
if errorlevel 1 ( echo. & echo [ERROR] Version bump failed. & popd & exit /b 1 )

popd
if not defined CI if not defined BATCH_NO_PAUSE pause
exit /b 0
