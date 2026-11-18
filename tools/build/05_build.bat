@echo off
setlocal enabledelayedexpansion
pushd "%~dp0"

REM ================================================================
REM  Build Software  (incremental)
REM  Compiles the application reusing the existing PyInstaller cache.
REM  Use 02_rebuild.bat for a full clean build from scratch.
REM ================================================================

echo.
echo [BUILD] %DATE% %TIME%
echo.

call "..\config\builder\builder_env.bat"
if errorlevel 1 ( echo [ERROR] Failed to load build environment. & popd & exit /b 1 )

REM --- Embed Git metadata into version index
REM     Reads the committed template, writes the artifact file (already gitignored via prj/build/).
REM     The committed prj/config/version/index.json is NEVER modified - no post-build commit needed.
echo [INFO] Generating version metadata...
call "%PYTHON%" "..\..\tools\build\scripts\generate_version.py" ^
    --template "..\..\prj\config\version\index.json" ^
    --output "%BUILD_DIR%\index.json"
if errorlevel 1 ( echo [WARN] Version metadata generation failed - continuing without it. )
echo.

call "%PYTHON%" "..\..\tools\build\scripts\build.py" --build
if errorlevel 1 ( echo. & echo [ERROR] Build failed. & popd & exit /b 1 )

REM --- Build Chocolatey NuGet package
echo.
echo [INFO] Building NuGet package...
call "%PYTHON%" "..\..\tools\build\scripts\build_nuget.py"
if errorlevel 1 ( echo [WARN] NuGet packaging failed - software build succeeded. )

echo.
echo [OK] Build completed successfully.
popd
if not defined CI if not defined BATCH_NO_PAUSE pause
exit /b 0
