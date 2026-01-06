@echo off
:: This batch file runs the PowerShell installer with the correct execution policy
:: Use this if double-clicking the .ps1 file doesn't work or closes too fast.

echo Starting School Bell Installer...
powershell -ExecutionPolicy Bypass -File install.ps1
pause
