@echo off
pushd %~dp0
setlocal enabledelayedexpansion

REM ============================================================
REM  Generate Ed25519 Key Pair
REM ============================================================

call ..\..\config\builder\builder_env.bat

echo.
echo ============================================================
echo Generating Ed25519 key pair
echo ============================================================
echo.

call %PYTHON% ..\..\..\tools\build\scripts\ed25519_key.py generate

if errorlevel 1 (
    echo [ERROR] Key generation failed.
    popd
    exit /b 1
)

echo.
echo Encrypting Ed25519 private key
echo.
call key_encrypt.bat

if errorlevel 1 (
    echo [ERROR] Private key encryption failed.
    popd
    exit /b 1
)

echo.
echo [SUCCESS] Ed25519 key pair generated and private key encrypted successfully.
echo.
pause
popd
exit /b 0