# IMPORTANT: Before releasing this package, copy/paste the next 2 lines into PowerShell to remove all comments from this file:
#   $f='c:\path\to\thisFile.ps1'
#   gc $f | ? {$_ -notmatch "^\s*#"} | % {$_ -replace '(^.*?)\s*?[^``]#.*','$1'} | Out-File $f+".~" -en utf8; mv -fo $f+".~" $f

## NOTE: In 80-90% of the cases (95% with licensed versions due to Package Synchronizer and other enhancements),
## AutoUninstaller should be able to detect and handle registry uninstalls without a chocolateyUninstall.ps1.
## See https://docs.chocolatey.org/en-us/choco/commands/uninstall
## and https://docs.chocolatey.org/en-us/create/functions/uninstall-chocolateypackage

## If this is an MSI, ensure 'softwareName' is appropriate, then clean up comments and you are done.
## If this is an exe, change fileType, silentArgs, and validExitCodes

$ErrorActionPreference = 'Stop'

# ------------------------------
# Configuration (must match install defaults)
# ------------------------------
$packageName = '{{APP_NAME}}'
$appName     = '{{APP_NAME}}'
$defaultInstallPath = "C:\Program Files\$appName"
$exeLinkName = "$appName.lnk"

# Allow custom install path via choco params: --params "'/InstallPath:C:\Apps\$appName'"
$pp = Get-PackageParameters
$installPath = if ($pp.InstallPath) { $pp.InstallPath } else { $defaultInstallPath }

Write-Host "Starting uninstall of $packageName..." -ForegroundColor Cyan
Write-Host "Using install path: $installPath" -ForegroundColor Cyan

# ------------------------------
# Remove shortcuts
# ------------------------------
$startMenuLink = Join-Path $Env:ProgramData "Microsoft\Windows\Start Menu\Programs\$exeLinkName"
$desktopLink   = Join-Path ([Environment]::GetFolderPath('Desktop')) $exeLinkName

foreach ($link in @($startMenuLink, $desktopLink)) {
    if (Test-Path $link) {
        Write-Host "Removing shortcut: $link" -ForegroundColor Yellow
        Remove-Item $link -Force -ErrorAction SilentlyContinue
    }
}

# ------------------------------
# Remove PATH entry (Machine)
# ------------------------------
$machinePath = [Environment]::GetEnvironmentVariable('PATH', 'Machine')
if ($machinePath -and ($machinePath -like "*$installPath*")) {
    Write-Host "Removing $installPath from system PATH" -ForegroundColor Yellow

    $parts = $machinePath -split ';' | Where-Object {
        $_ -and ($_.TrimEnd('\') -ne $installPath.TrimEnd('\'))
    }

    $newPath = ($parts -join ';').TrimEnd(';')
    [Environment]::SetEnvironmentVariable('PATH', $newPath, 'Machine')
}

# ------------------------------
# Run vendor uninstall (setup.bat -1) if present
# ------------------------------
$setupBat = Join-Path $installPath '_internal\setup.bat'
if (Test-Path $setupBat) {
    Write-Host "Found setup.bat — running uninstall: `"$setupBat -1`"" -ForegroundColor Cyan
    $proc = Start-Process -FilePath 'cmd.exe' -ArgumentList "/c `"$setupBat`" < nul -1" -WorkingDirectory $installPath -NoNewWindow -Wait -PassThru
    if ($proc.ExitCode -ne 0) {
        Write-Warning "setup.bat uninstall exited with code $($proc.ExitCode)"
        throw "Vendor uninstall (setup.bat -1) failed with exit code $($proc.ExitCode)"
    } else {
        Write-Host "Vendor uninstall completed successfully." -ForegroundColor Green
    }
} else {
    Write-Host "No setup.bat found; skipping vendor uninstall." -ForegroundColor Yellow
}

# ------------------------------
# Remove installed files
# ------------------------------
if (Test-Path $installPath) {
    Write-Host "Removing install directory: $installPath" -ForegroundColor Yellow
    Remove-Item $installPath -Recurse -Force
} else {
    Write-Warning "Install directory not found: $installPath"
}

Write-Host "$packageName uninstalled successfully." -ForegroundColor Green
Write-Host "You may need to restart your terminal/session for PATH changes to apply." -ForegroundColor Yellow

## OTHER POWERSHELL FUNCTIONS
## https://docs.chocolatey.org/en-us/create/functions
#Uninstall-ChocolateyZipPackage $packageName # Only necessary if you did not unpack to package directory - see https://docs.chocolatey.org/en-us/create/functions/uninstall-chocolateyzippackage
#Uninstall-ChocolateyEnvironmentVariable - https://docs.chocolatey.org/en-us/create/functions/uninstall-chocolateyenvironmentvariable
#Uninstall-BinFile # Only needed if you used Install-BinFile - see https://docs.chocolatey.org/en-us/create/functions/uninstall-binfile
## Remove any shortcuts you added in the install script.

