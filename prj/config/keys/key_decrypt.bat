@echo off
pushd %~dp0
setlocal enabledelayedexpansion

REM ============================================================
REM  Decrypt Encrypted Ed25519 Private Key
REM ============================================================

call ..\..\config\builder\builder_env.bat

echo.
echo ============================================================
echo Decrypting Encrypted Private Key
echo ============================================================
echo.

call %PYTHON% ..\..\..\tools\build\scripts\ed25519_key.py decrypt

if errorlevel 1 (
    echo [ERROR] Decryption failed.
    popd
    exit /b 1
)

echo.
echo [SUCCESS] Private key decrypted
echo.
pause
popd
exit /b 0
