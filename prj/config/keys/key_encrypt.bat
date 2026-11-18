@echo off
pushd %~dp0
setlocal enabledelayedexpansion

REM ============================================================
REM  Encrypt existing Ed25519 Private Key
REM ============================================================

call ..\..\config\builder\builder_env.bat

echo.
echo ============================================================
echo Encrypting Private Key
echo ============================================================
echo.

call %PYTHON% ..\..\..\tools\build\scripts\ed25519_key.py encrypt

if errorlevel 1 (
    echo [ERROR] Encryption failed.
    popd
    exit /b 1
)

echo.
echo [SUCCESS] Private key encrypted %ENC_KEY%
echo.
pause
popd
exit /b 0
