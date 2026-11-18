@REM ===========================================
@REM Environment setup for resource build tools
@REM ===========================================

REM Get the directory of this script (builder_env.bat)
set BUILDER_ENV_DIR=%~dp0

REM Remove trailing backslash if present
if "%BUILDER_ENV_DIR:~-1%"=="\" set "BUILDER_ENV_DIR=%BUILDER_ENV_DIR:~0,-1%"

REM Path to the python virtual environment folder
set PYTHON_VENV=%BUILDER_ENV_DIR%\..\..\..\.venv

@REM ---- Python Executables ----
@REM Set Python interpreter (requirement: Python 3.11+)
@REM Example: C:\Python311\python.exe
set PYTHON=%PYTHON_VENV%\Scripts\python.exe

@REM Set UI-to-Python converter (requirement: pyuic6 or pyside6-uic)
@REM Example: C:\Python311\Scripts\pyside6-uic.exe
set PYUIC=%PYTHON_VENV%\Scripts\pyside6-uic.exe

@REM Set Qt resource compiler (requirement: pyside6-rcc or pyrcc6)
@REM Example: C:\Python311\Scripts\pyside6-rcc.exe
set PYRCC=%PYTHON_VENV%\Scripts\pyside6-rcc.exe

@REM Set Qt Designer executable (requirement: Qt6 Designer)
@REM Example: C:\Python311\Lib\site-packages\qt6_applications\Qt\bin\pyside6-designer.exe
set QTDESIGNER=%PYTHON_VENV%\Scripts\pyside6-designer.exe

@REM Set raster-to-SVG converter (requirement: vtracer)
@REM Example: ..\tools\vtracer\vtracer.exe
set VTRACER=..\..\tools\vtracer\vtracer.exe

@REM ---- Project Directories ----
@REM Directory containing Designer .ui files
@REM Example: ..\..\src\app\view\widgets\ui
set QTDESIGNER_UI_DIR=..\..\src\app\view\widgets\ui

@REM Directory for generated .py files from .ui files
@REM Example: ..\..\src\app\view\widgets
set QTDESIGNER_PY_DIR=..\..\src\app\view\widgets

@REM Qt resource file (.qrc) path
@REM Example: ..\..\src\qt_embedded\resources.qrc
set RESOURCE_QRC_FILE=..\..\src\qt_embedded\resources.qrc

@REM Directory for generated .py files from .qrc files
@REM Example: ..\..\src\qt_embedded
set RESOURCE_PY_DIR=..\..\src\qt_embedded

@REM Python import statement for compiled Qt resource module
@REM Example: from qt_embedded import resources_rc
set RESOURCE_IMPORT=from qt_embedded import resources

@REM Directory containing original raster images for SVG conversion
@REM Example: ..\..\src\qt_embedded\originals
set IMAGE_DIR=..\..\src\qt_embedded\originals

@REM Directory for generated SVG icons
@REM Example: ..\..\src\qt_embedded\icons
set SVG_DIR=..\..\src\qt_embedded\icons

@REM ---- Artifactory Deployment Variables ----
set ARTIFACTORY_URL=https://artifactory.example.com/artifactory
set PACKAGE_REPO=bgsv-eds-tool-generic-release-local/tool-packages/LabMango
set META_REPO=bgsv-eds-tool-generic-release-local/tool-metadata/LabMango
set NUGET_REPO=bgsv-eds-tool-nuget-release-local/labmango
set BUILD_DIR=..\..\prj\build\app

@REM ===========================================
@REM End of environment setup
@REM ===========================================
