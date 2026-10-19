# Run as the same Windows user who installed the startup task.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'This script requires Windows.' }
$Task = Get-ScheduledTask -TaskName 'Plex PC Remote' -ErrorAction SilentlyContinue
if ($Task) {
    Stop-ScheduledTask -InputObject $Task
    Unregister-ScheduledTask -InputObject $Task -Confirm:$false
    Write-Host 'Server task stopped and startup removed. Plex and config files are unchanged.'
} else {
    Write-Host 'Startup task is not installed.'
}
