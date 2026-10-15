# Run from PowerShell as the same user who runs Plex. No administrator needed.
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot '.venv\Scripts\pythonw.exe'
$ConfigFile = Join-Path $ProjectRoot 'server\config.json'
if (!(Test-Path $PythonExe) -or !(Test-Path $ConfigFile)) {
    throw 'First create .venv, install requirements and run python -m server.setup.'
}
$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument ('-m server.app --config "{0}"' -f $ConfigFile) -WorkingDirectory $ProjectRoot
$Account = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $Account
$Principal = New-ScheduledTaskPrincipal -UserId $Account -LogonType Interactive -RunLevel Limited
$Settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName 'Plex PC Remote' -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Description 'Plex HTPC remote in the interactive user session' -Force
Write-Host 'Registered. Starts at next logon. To start now: Start-ScheduledTask -TaskName "Plex PC Remote"'
