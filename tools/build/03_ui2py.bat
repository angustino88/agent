@echo off
setlocal enabledelayedexpansion
pushd "%~dp0"

REM ================================================================
REM  UI to Python
REM  Compiles Qt Designer .ui files into Python source modules.
REM ================================================================

echo.
echo [UI2PY] %DATE% %TIME%
echo.

call "..\config\builder\builder_env.bat"
if errorlevel 1 ( echo [ERROR] Failed to load build environment. & popd & exit /b 1 )

call "%PYTHON%" "..\..\tools\build\scripts\ui2py.py" "%PYUIC%" "%QTDESIGNER_UI_DIR%" "%QTDESIGNER_PY_DIR%" "%RESOURCE_IMPORT%"
if errorlevel 1 ( echo. & echo [ERROR] UI compilation failed. & popd & exit /b 1 )

echo.
echo [OK] UI files compiled successfully.
popd
if not defined CI if not defined BATCH_NO_PAUSE pause
exit /b 0
