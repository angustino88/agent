$ErrorActionPreference = 'Stop'

# ------------------------------
# Configuration
# ------------------------------
$packageName   = '{{APP_NAME}}'
$appName       = '{{APP_NAME}}'
$zipFileName   = "$appName-${env:ChocolateyPackageVersion}.zip"
$installPath   = "C:\Program Files\$appName"
$exeFileName   = "$appName.exe"
$createDesktopShortcut = $true
$noRemoveExisting = $true

# Allow custom install path via choco params: --params "'/InstallPath:C:\Apps\$appName'"
$pp = Get-PackageParameters
if ($pp.InstallPath) {
    $installPath = $pp.InstallPath
}

# Allow custom behavior:
# --params "'/InstallPath:C:\Apps\HexView /NoRemoveExisting:true'"
$pp = Get-PackageParameters

if ($pp.NoRemoveExisting) {
    $noRemoveExisting = [System.Convert]::ToBoolean($pp.NoRemoveExisting)
}

# Resolve script path
$toolsDir  = "$(Split-Path -Parent $MyInvocation.MyCommand.Definition)"
$zipPath   = Join-Path $toolsDir $zipFileName
$exePath   = Join-Path $installPath $exeFileName

Write-Host "Starting installation of $packageName..." -ForegroundColor Cyan

# ------------------------------
# Clean previous installation
# ------------------------------
if ((Test-Path $installPath) -and -not $noRemoveExisting) {
    Write-Host "Removing previous version from $installPath" -ForegroundColor Yellow
    Remove-Item $installPath -Recurse -Force
} elseif (Test-Path $installPath) {
    Write-Host "Existing install detected; leaving files in place (NoRemoveExisting=true)" -ForegroundColor Yellow
}

# ------------------------------
# Create installation directory
# ------------------------------
Write-Host "Creating installation directory: $installPath"
New-Item -Path $installPath -ItemType Directory -Force | Out-Null

# ------------------------------
# Extract ZIP
# ------------------------------
if (!(Test-Path $zipPath)) {
    throw "ERROR: ZIP file not found: $zipPath"
}

Write-Host "Extracting $zipFileName to $installPath ..."
Expand-Archive -Path $zipPath -DestinationPath $installPath -Force

# ------------------------------
# Add to PATH (if not already exists)
# ------------------------------
$envPath = [Environment]::GetEnvironmentVariable('PATH', 'Machine')
if ($envPath -notlike "*$installPath*") {
    Write-Host "Adding $installPath to system PATH"
    [Environment]::SetEnvironmentVariable('PATH', "$envPath;$installPath", 'Machine')
}

# ------------------------------
# Create Start Menu Shortcut
# ------------------------------
$startMenuPath = Join-Path $Env:ProgramData "Microsoft\Windows\Start Menu\Programs\$appName.lnk"

if (Test-Path $exePath) {
    Write-Host "Creating Start Menu shortcut for $appName..."
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($startMenuPath)
    $shortcut.TargetPath = $exePath
    $shortcut.WorkingDirectory = $installPath
    $shortcut.WindowStyle = 1
    $shortcut.Description = "$appName Binary Viewer"
    $shortcut.Save()
} else {
    Write-Warning "Executable not found at $exePath - Start Menu shortcut not created."
}

# ------------------------------
# Create Desktop Shortcut (optional)
# ------------------------------
if ($createDesktopShortcut -and (Test-Path $exePath)) {
    Write-Host "Creating Desktop shortcut..."
    $desktopPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "$appName.lnk"
    Copy-Item $startMenuPath $desktopPath -Force
}

# ------------------------------
# Create installation marker
# ------------------------------
$markerFile = Join-Path $installPath "choco_installed.txt"
Set-Content -Path $markerFile -Value "Installed $appName via Chocolatey on $(Get-Date)"

Write-Host "$appName installed successfully to $installPath" -ForegroundColor Green
Write-Host "You may need to restart your terminal to apply PATH changes." -ForegroundColor Yellow

# ------------------------------
# Run vendor setup.bat if present
# ------------------------------
$setupBat = Join-Path $installPath '_internal\setup.bat'
if (Test-Path $setupBat) {
    Write-Host "Found setup.bat — running in $installPath" -ForegroundColor Cyan
    $proc = Start-Process -FilePath 'cmd.exe' -ArgumentList "/c `"$setupBat`" < nul" -WorkingDirectory $installPath -NoNewWindow -Wait -PassThru
    if ($proc.ExitCode -ne 0) {
        Write-Warning "setup.bat exited with code $($proc.ExitCode)"
        throw "setup.bat failed with exit code $($proc.ExitCode)"
    }
} else {
    Write-Host "No setup.bat found; skipping vendor setup." -ForegroundColor Yellow
}