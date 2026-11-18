@echo off
setlocal enabledelayedexpansion
pushd "%~dp0"

REM ================================================================
REM  Build Resources
REM  Three-stage pipeline:
REM    1. Raster images  -->  SVG         (via vtracer)
REM    2. SVG files      -->  .qrc manifest
REM    3. .qrc manifest  -->  Python module  (via pyside6-rcc)
REM ================================================================

echo.
echo [RESOURCES] %DATE% %TIME%
echo.

call "..\config\builder\builder_env.bat"
if errorlevel 1 ( echo [ERROR] Failed to load build environment. & popd & exit /b 1 )

echo [1/3] Converting raster images to SVG...
if exist "%SVG_DIR%" del /q "%SVG_DIR%\*.svg" 2>nul
call "%PYTHON%" "..\..\tools\build\scripts\img2svg.py" "%VTRACER%" "%IMAGE_DIR%" "%SVG_DIR%"
if errorlevel 1 ( echo [ERROR] Image-to-SVG conversion failed. & popd & exit /b 1 )

echo [2/3] Generating .qrc manifest...
call "%PYTHON%" "..\..\tools\build\scripts\files2qrc.py" "%SVG_DIR%" "%RESOURCE_QRC_PREFIX%" "%RESOURCE_QRC_FILE%"
if errorlevel 1 ( echo [ERROR] QRC manifest generation failed. & popd & exit /b 1 )

echo [3/3] Compiling .qrc to Python module...
call "%PYTHON%" "..\..\tools\build\scripts\qrc2py.py" "%PYRCC%" "%RESOURCE_QRC_FILE%" "%RESOURCE_PY_DIR%"
if errorlevel 1 ( echo [ERROR] QRC compilation failed. & popd & exit /b 1 )

echo.
echo [OK] Resources built successfully.
popd
if not defined CI if not defined BATCH_NO_PAUSE pause
exit /b 0
