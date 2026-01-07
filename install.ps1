# School Bell System - Installation Script (Native Windows)
# This script "installs" the app by moving it to a safe place and creating icons.

$AppName = "SchoolBell"
$DisplayName = "School Bell System"
$InstallDir = Join-Path $env:LOCALAPPDATA $AppName
$ExeSource = "dist\SchoolBell.exe"
$IconSource = "static\school-logo.png"

Write-Host "--- $DisplayName Installation ---" -ForegroundColor Cyan

# 1. Check if the EXE exists in dist folder
if (-not (Test-Path $ExeSource)) {
    Write-Host "Error: Could not find '$ExeSource'." -ForegroundColor Red
    Write-Host "Please run the PyInstaller build command first to create the 'dist\SchoolBell.exe' file." -ForegroundColor Yellow
    Write-Host "`nPress any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit
}

# 2. Create the Installation Directory
if (-not (Test-Path $InstallDir)) {
    Write-Host "Creating folder: $InstallDir"
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

# 3. Copy the Executable
Write-Host "Copying $AppName to installation folder..."
Copy-Item $ExeSource (Join-Path $InstallDir "$AppName.exe") -Force

# 4. Create Desktop Shortcut
Write-Host "Creating Desktop shortcut..."
$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Desktop)
$Shortcut = $WshShell.CreateShortcut((Join-Path $DesktopPath "$DisplayName.lnk"))
$Shortcut.TargetPath = (Join-Path $InstallDir "$AppName.exe")
$Shortcut.WorkingDirectory = $InstallDir
$Shortcut.IconLocation = (Join-Path $InstallDir "$AppName.exe,0") # Uses the icon bundled in the EXE
$Shortcut.Save()

# 5. Create Start Menu Shortcut
Write-Host "Adding to Start Menu..."
$StartMenuPath = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Programs)
$Shortcut = $WshShell.CreateShortcut((Join-Path $StartMenuPath "$DisplayName.lnk"))
$Shortcut.TargetPath = (Join-Path $InstallDir "$AppName.exe")
$Shortcut.WorkingDirectory = $InstallDir
$Shortcut.Save()

# 6. Register for Auto-Start (Multi-Method for maximum reliability)
Write-Host "Registering for Auto-Start on Boot..."
$ExePath = (Join-Path $InstallDir "$AppName.exe")

# Method A: Task Scheduler (The most reliable for "At Boot" on Laptops)
# Creates a task that ignores "AC Power" restrictions
try {
    $action = New-ScheduledTaskAction -Execute $ExePath
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    Register-ScheduledTask -TaskName $AppName -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force | Out-Null
    Write-Host "  - Task Scheduler: SUCCESS" -ForegroundColor Gray
} catch {
    Write-Host "  - Task Scheduler: FAILED (Fallback to Registry only)" -ForegroundColor Yellow
}

# Method B: Registry Run Key
New-ItemProperty `
  -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" `
  -Name $AppName `
  -Value "`"$ExePath`"" `
  -PropertyType String `
  -Force | Out-Null
Write-Host "  - Registry: SUCCESS" -ForegroundColor Gray

Write-Host "`n--- Success! ---" -ForegroundColor Green
Write-Host "The $DisplayName has been installed."
Write-Host "Launching the app now to register system settings..."

# Launch the app from the new location
Start-Process (Join-Path $InstallDir "$AppName.exe")

Write-Host "You can also open it any time from your Desktop or Start Menu."
Write-Host "Close this window to finish."
pause
