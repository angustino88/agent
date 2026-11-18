@echo off
setlocal enabledelayedexpansion
pushd "%~dp0"

REM ================================================================
REM  Release
REM  Full release pipeline: clean rebuild followed by deployment.
REM
REM  Usage:  08_release.bat [--force]
REM    --force   Re-deploy even if this version is already in index.json.
REM
REM  Prerequisites:
REM    ARTIFACTORY_TOKEN  must be set in the environment.
REM ================================================================

echo.
echo =============================================================
echo   RELEASE  %DATE% %TIME%
echo =============================================================
echo.

REM Load build environment so PYTHON is available for the git tag step
call "..\config\builder\builder_env.bat"
if errorlevel 1 ( echo [ERROR] Failed to load build environment. & popd & exit /b 1 )

REM Suppress interactive pauses and prompts in called scripts
set BATCH_NO_PAUSE=1

REM --- Step 1: Clean rebuild
echo [STEP 1/3] Clean rebuild...
echo.
call 06_rebuild.bat
if errorlevel 1 ( echo. & echo [ERROR] Build failed. Deployment aborted. & popd & exit /b 1 )

echo.
REM --- Step 2: Deploy
echo [STEP 2/3] Deploying to Artifactory...
echo.
call 11_artifactory_deploy.bat %*
if errorlevel 1 ( echo. & echo [ERROR] Deployment failed. & popd & exit /b 1 )

echo.
REM --- Step 3: Git tag
echo [STEP 3/3] Creating git tag...
call "%PYTHON%" "..\..\tools\build\scripts\tag_release.py"
if errorlevel 1 ( echo [WARN] Git tagging failed - continuing. )

echo.
echo =============================================================
echo   [OK] Release completed successfully.  %DATE% %TIME%
echo =============================================================
echo.
popd
if not defined CI pause
exit /b 0
