@echo off
setlocal enabledelayedexpansion
pushd "%~dp0"

REM ================================================================
REM  Artifactory Deploy (tools)
REM  Uploads the build package (.zip), meta.json, and index.json
REM  to the configured Artifactory repositories.
REM
REM  This file is the tools-level wrapper. It mirrors the behavior of
REM  prj/build/11_artifactory_deploy.bat but uses local script paths.
REM ================================================================

echo.
echo [DEPLOY] %DATE% %TIME%
echo.

REM --- Load builder environment (resolve relative to workspace)
call "..\..\prj\config\builder\builder_env.bat"
if errorlevel 1 ( echo [ERROR] Failed to load build environment. & popd & exit /b 1 )

REM --- Validate required variables via subroutine
for %%V in (BUILD_DIR ARTIFACTORY_URL PACKAGE_REPO META_REPO PYTHON) do call :_check_env_var %%V
goto :_env_check_done

:_check_env_var
if not defined %1 (
    echo [ERROR] Required variable %1 is not defined in builder_env.bat.
    popd
    exit /b 1
)
goto :eof

:_env_check_done

REM --- Prompt for ARTIFACTORY_TOKEN if needed
if defined ARTIFACTORY_TOKEN goto :_token_ok
if defined CI (
    echo [ERROR] ARTIFACTORY_TOKEN is not set in CI environment.
    popd
    exit /b 1
)
set /p ARTIFACTORY_TOKEN=Please enter your ARTIFACTORY_TOKEN: 
if not defined ARTIFACTORY_TOKEN (
    echo [ERROR] No ARTIFACTORY_TOKEN entered. Aborting.
    popd
    exit /b 1
)
:_token_ok

REM --- Ensure ARTIFACTORY_TOKEN is not empty or whitespace
set "TOKEN_TRIM=%ARTIFACTORY_TOKEN: =%"
if "%TOKEN_TRIM%"=="" (
    echo [ERROR] ARTIFACTORY_TOKEN is empty or whitespace. Aborting.
    popd
    exit /b 1
)

REM --- Locate build artifacts
set "PACKAGE_PATH="
set "META_PATH="
set "INDEX_PATH="

for %%f in ("%BUILD_DIR%\*.zip") do (
    set "PACKAGE_PATH=%%~f"
    goto :found_zip
)
:found_zip

for %%f in ("%BUILD_DIR%\meta.json") do (
    set "META_PATH=%%~f"
    goto :found_meta
)
:found_meta

for %%f in ("%BUILD_DIR%\index.json") do (
    set "INDEX_PATH=%%~f"
    goto :found_index
)
:found_index

set "NUGET_PATH="
for %%f in ("%BUILD_DIR%\*.nupkg") do (
    set "NUGET_PATH=%%~f"
    goto :found_nuget
)
:found_nuget

REM --- Validate found files
if not defined PACKAGE_PATH (
    echo [ERROR] No .zip package found in "%BUILD_DIR%"
    popd
    exit /b 1
)

if not defined INDEX_PATH (
    echo [INFO] No index.json found in "%BUILD_DIR%". Skipping index upload.
)

if not defined META_PATH (
    echo [ERROR] No meta.json found in "%BUILD_DIR%"
    popd
    exit /b 1
)

REM --- Show deployment summary
echo.
echo =============================================================
echo                 Artifactory Deployment Info
echo =============================================================
echo ARTIFACTORY_URL  : %ARTIFACTORY_URL%
echo PACKAGE_REPO     : %PACKAGE_REPO%
echo META_REPO        : %META_REPO%
echo -------------------------------------------------------------
echo Package File     : %PACKAGE_PATH%
echo Index File       : %INDEX_PATH%
echo Meta File        : %META_PATH%
echo NuGet Repository : %NUGET_REPO%
echo NuGet File       : %NUGET_PATH%
echo =============================================================
echo.

set "INDEX_PATH="
choice /C YN /M "Upload index.json to Artifactory?"
if errorlevel 2 (
    echo [INFO] Index upload skipped by user.
) else (
    for %%f in ("%BUILD_DIR%\index.json") do (
        set "INDEX_PATH=%%~f"
    )
    if not defined INDEX_PATH (
        echo [INFO] No index.json found in "%BUILD_DIR%". Skipping index upload.
    )
)

set "NUGET_UPLOAD_REPO="
set "NUGET_UPLOAD_PATH="
if defined NUGET_PATH (
    choice /C YN /M "Upload NuGet package to Artifactory?"
    if errorlevel 1 (
        set "NUGET_UPLOAD_REPO=%NUGET_REPO%"
        set "NUGET_UPLOAD_PATH=%NUGET_PATH%"
    ) else (
        echo [INFO] NuGet package upload skipped by user.
    )
) else (
    echo [INFO] No .nupkg found in "%BUILD_DIR%". Skipping NuGet upload.
)

REM --- Confirm deployment
if not defined CI if not defined BATCH_NO_PAUSE (
    choice /C YN /M "Proceed with deployment?"
    if errorlevel 2 (
        echo [INFO] Deployment cancelled by user.
        popd
        exit /b 0
    )
)

REM --- Deploy artifacts (use local scripts folder)
echo [INFO] Deploying to Artifactory...
echo.
call "%PYTHON%" "..\..\tools\build\scripts\artifactory_deploy.py" ^
    "%ARTIFACTORY_URL%" "%PACKAGE_REPO%" "%META_REPO%" ^
    "%ARTIFACTORY_TOKEN%" "%PACKAGE_PATH%" "%META_PATH%" "%INDEX_PATH%" ^
    "%NUGET_UPLOAD_REPO%" "%NUGET_UPLOAD_PATH%" %*

if errorlevel 1 (
    echo [ERROR] Deployment failed.
    popd
    exit /b 1
)

echo.
echo [SUCCESS] Deployment completed successfully.
echo.

REM ================================================================
REM  Create and push release tag (on current HEAD)
REM ================================================================
echo [INFO] Creating release tag...
echo.

set "APP_VERSION="
for /f "usebackq delims=" %%V in (`"%PYTHON%" "..\..\tools\build\scripts\generate_version.py" --output "%INDEX_PATH%" --print-version 2^>nul`) do set "APP_VERSION=%%V"

if not defined APP_VERSION (
    echo [WARN] Could not determine version from index.json - skipping release tag.
    goto :skip_tag
)

set "TAG_NAME=v%APP_VERSION%"

REM --- Use current HEAD as the tag target (explicit requirement)
for /f "usebackq delims=" %%S in ('git rev-parse --short HEAD 2^>nul') do set "GIT_SHORT=%%S"
set "TAG_MSG=Release %TAG_NAME% (git: %GIT_SHORT%)"

REM --- Validate HEAD exists
git cat-file -t HEAD >nul 2>&1
if errorlevel 1 (
    echo [WARN] HEAD not available - skipping tag creation.
    goto :skip_tag
)

git tag -a "%TAG_NAME%" -m "%TAG_MSG%" HEAD
if errorlevel 1 (
    echo [WARN] Tag %TAG_NAME% already exists or tagging failed - skipping push.
    goto :skip_tag
)
echo [INFO] Created tag: %TAG_NAME% -> HEAD (%GIT_SHORT%)

REM --- Decide whether to push the tag automatically
set "PUSH_TAG=0"
if /I "%RELEASE_PUSH%"=="1" set "PUSH_TAG=1"
if /I "%RELEASE_PUSH%"=="true" set "PUSH_TAG=1"
if /I "%RELEASE_PUSH%"=="yes" set "PUSH_TAG=1"

if "%PUSH_TAG%"=="1" (
    echo [INFO] RELEASE_PUSH=%RELEASE_PUSH% - pushing tag automatically.
    git push origin "%TAG_NAME%"
    if errorlevel 1 (
        echo [WARN] Failed to push tag %TAG_NAME%. Push manually:  git push origin %TAG_NAME%
    ) else (
        echo [INFO] Tag %TAG_NAME% pushed to remote.
    )
) else (
    if defined CI (
        echo [WARN] Non-interactive environment; skipping tag push. Set RELEASE_PUSH=1 to enable automatic push in CI.
    ) else (
        if defined BATCH_NO_PAUSE (
            echo [WARN] Non-interactive environment; skipping tag push. Set RELEASE_PUSH=1 to enable automatic push in CI.
        ) else (
            choice /C YN /M "Push tag %TAG_NAME% to remote? (Y=push / N=skip)"
            if errorlevel 2 (
                echo [INFO] Skipping tag push.
            ) else (
                git push origin "%TAG_NAME%"
                if errorlevel 1 (
                    echo [WARN] Failed to push tag %TAG_NAME%. Push manually:  git push origin %TAG_NAME%
                ) else (
                    echo [INFO] Tag %TAG_NAME% pushed to remote.
                )
            )
        )
    )
)

:skip_tag
echo.
popd
if not defined CI if not defined BATCH_NO_PAUSE pause
exit /b 0
