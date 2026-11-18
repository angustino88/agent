@echo off
setlocal enabledelayedexpansion
pushd "%~dp0"

REM ================================================================
REM  CHANGELOG.md Generator
REM  Generates CHANGELOG.md from git tag history and commit subjects.
REM  Each version tag becomes one section in the output file.
REM
REM  Usage:  12_changelog.bat [--stdout] [--since TAG] [--max N]
REM    --stdout      print to console instead of writing file
REM    --since TAG   include only versions >= TAG
REM    --max N       include at most N version tags (default: 50)
REM ================================================================

echo.
echo [CHANGELOG] %DATE% %TIME%
echo.

call "..\config\builder\builder_env.bat"
if errorlevel 1 ( echo [ERROR] Failed to load build environment. & popd & exit /b 1 )

call "%PYTHON%" "..\..\tools\build\scripts\changelog_gen.py" %*
if errorlevel 1 ( echo. & echo [ERROR] Changelog generation failed. & popd & exit /b 1 )

popd
if not defined CI if not defined BATCH_NO_PAUSE pause
exit /b 0
