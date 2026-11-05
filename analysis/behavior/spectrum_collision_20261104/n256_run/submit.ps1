$ErrorActionPreference = 'Stop'
$dir = 'D:\Temp\SAR20N256_20261104_qfhxXr'
$taskName = 'SAR20_N256_20261104_qfhxXr'
$existing = Get-ScheduledTask -TaskName 'SAR20_MatlabControl' -ErrorAction Stop
if ([string]$existing.State -ne 'Ready') { throw 'Existing SAR20 task is not idle.' }
$process = @(Get-Process -Name MATLAB -ErrorAction Stop)
if ($process.Count -ne 1 -or $process[0].Id -ne 27628 -or -not $process[0].Responding) { throw 'Expected one responsive MATLAB PID 27628.' }
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) { throw 'Task name already exists; do not resubmit.' }
$busy = @(Get-ScheduledTask | Where-Object { $_.TaskName -like 'SAR20*' -and [string]$_.State -eq 'Running' })
if ($busy.Count -ne 0) { throw 'Another SAR20 task is already running.' }
$xml = Export-ScheduledTask -TaskName 'SAR20_MatlabControl'
[IO.File]::WriteAllText((Join-Path $dir 'existing_task_before.xml'), $xml, [Text.UTF8Encoding]::new($false))
$arguments = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "D:/Temp/SAR20N256_20261104_qfhxXr/controller.ps1"'
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments -WorkingDirectory 'D:\Academic\Projects\sar20m1\SAR20'
Register-ScheduledTask -TaskName $taskName -Action $action -Principal $existing.Principal -Settings $existing.Settings | Out-Null
Start-ScheduledTask -TaskName $taskName
[PSCustomObject]@{ TaskName=$taskName; State=(Get-ScheduledTask -TaskName $taskName).State; MatlabPid=$process[0].Id } | ConvertTo-Json -Compress
