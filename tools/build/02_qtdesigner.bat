@echo off
setlocal enabledelayedexpansion
pushd "%~dp0"

REM ================================================================
REM  Qt Designer
REM  Opens Qt Designer with the project UI source directory.
REM ================================================================

echo.
echo [QT DESIGNER] %DATE% %TIME%
echo.

call "..\config\builder\builder_env.bat"
if errorlevel 1 ( echo [ERROR] Failed to load build environment. & popd & exit /b 1 )

call "%PYTHON%" "..\..\tools\build\scripts\qtdesigner.py" "%QTDESIGNER%" "%QTDESIGNER_UI_DIR%"
if errorlevel 1 ( echo. & echo [ERROR] Qt Designer launch failed. & popd & exit /b 1 )

popd
exit /b 0
