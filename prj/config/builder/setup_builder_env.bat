@echo off
xcopy /I /Q /Y /F "../../../tools/build" "../../build" > nul
echo Build environment has been created
pause