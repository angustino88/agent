@echo off
setlocal enabledelayedexpansion

REM set mode from the first argument passed to the script
set mode=%1

REM define the application file name
set app_name=APP_NAME

REM resolve the app root directory one level above the bundle folder
for %%I in ("%~dp0..") do set "app_root=%%~fI"

REM define the task name
set task_name=%app_name%

REM define the executable file path
set exec_file=%app_root%\%app_name%.exe

rem define the output XML file path in the bundle directory
set "xml_file=%~dp0schtasks.xml"

REM write XML content to the file
(
echo ^<?xml version="1.0" encoding="UTF-16"?^>
echo ^<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task"^>
echo   ^<Triggers^>
echo     ^<SessionStateChangeTrigger^>
echo       ^<Enabled^>true^</Enabled^>
echo       ^<StateChange^>RemoteConnect^</StateChange^>
echo     ^</SessionStateChangeTrigger^>
echo     ^<BootTrigger^>
echo       ^<Enabled^>true^</Enabled^>
echo     ^</BootTrigger^>
echo     ^<CalendarTrigger^>
echo       ^<Repetition^>
echo         ^<Interval^>PT1H^</Interval^>
echo         ^<StopAtDurationEnd^>false^</StopAtDurationEnd^>
echo       ^</Repetition^>
echo       ^<StartBoundary^>2024-01-01T00:00:00^</StartBoundary^>
echo       ^<Enabled^>true^</Enabled^>
echo       ^<ScheduleByDay^>
echo         ^<DaysInterval^>1^</DaysInterval^>
echo       ^</ScheduleByDay^>
echo     ^</CalendarTrigger^>
echo   ^</Triggers^>
echo   ^<Settings^>
echo     ^<MultipleInstancesPolicy^>Parallel^</MultipleInstancesPolicy^>
echo     ^<DisallowStartIfOnBatteries^>true^</DisallowStartIfOnBatteries^>
echo     ^<StopIfGoingOnBatteries^>true^</StopIfGoingOnBatteries^>
echo     ^<AllowHardTerminate^>true^</AllowHardTerminate^>
echo     ^<StartWhenAvailable^>false^</StartWhenAvailable^>
echo     ^<RunOnlyIfNetworkAvailable^>false^</RunOnlyIfNetworkAvailable^>
echo     ^<IdleSettings^>
echo       ^<StopOnIdleEnd^>true^</StopOnIdleEnd^>
echo       ^<RestartOnIdle^>false^</RestartOnIdle^>
echo     ^</IdleSettings^>
echo     ^<AllowStartOnDemand^>true^</AllowStartOnDemand^>
echo     ^<Enabled^>true^</Enabled^>
echo     ^<Hidden^>false^</Hidden^>
echo     ^<RunOnlyIfIdle^>false^</RunOnlyIfIdle^>
echo     ^<WakeToRun^>false^</WakeToRun^>
echo     ^<ExecutionTimeLimit^>PT72H^</ExecutionTimeLimit^>
echo     ^<Priority^>7^</Priority^>
echo   ^</Settings^>
echo     ^<Principals^>
echo       ^<Principal id="Author"^>
echo         ^<GroupId^>Users^</GroupId^>
echo         ^<RunLevel^>HighestAvailable^</RunLevel^>
echo       ^</Principal^>
echo      ^</Principals^>
echo   ^<Actions Context="Author"^>
echo     ^<Exec^>
echo       ^<Command^>%exec_file%^</Command^>
echo       ^<WorkingDirectory^>%app_root%^</WorkingDirectory^>
echo     ^</Exec^>
echo   ^</Actions^>
echo ^</Task^>
) > "%xml_file%"

if !mode! neq -1 (
    echo Creating task in Task Scheduler
    schtasks /query /tn %task_name% >NUL 2>&1
    if %errorlevel% equ 0 schtasks /delete /tn %task_name% /f >NUL 2>&1
    schtasks /create /tn %task_name% /xml "%xml_file%"

    echo Creating task in Windows Registry
    rem Trigger at startup in task scheduler not working. Add the executable file to registry below for startup.
    reg add "HKEY_CURRENT_USER\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /v %task_name% /t REG_SZ /d %exec_file% /f

) else (
    echo Deleting task in Task Scheduler
    schtasks /query /tn %task_name% >NUL 2>&1
    if %errorlevel% equ 0 schtasks /delete /tn %task_name% /f

    echo Deleting task in Windows Registry
    reg delete "HKEY_CURRENT_USER\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /v %task_name% /f
)

pause