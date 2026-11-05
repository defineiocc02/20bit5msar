param([Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedParametersSha256)
$ErrorActionPreference='Stop';$job='D:\Temp\SAR20NORMAL_20261104_NX';$taskName='SAR20_NORMAL_RECOVER_20261104_NX'
foreach($dir in @('D:\Temp',$job)){ $i=Get-Item -LiteralPath $dir -Force;if(-not $i.PSIsContainer -or ($i.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw "Unsafe directory: $dir"} }
foreach($name in @('recovery.lock','recovery_status.json','gates/test_normal_10v','profile')){if($null -ne (Get-Item -LiteralPath (Join-Path $job $name) -Force -ErrorAction SilentlyContinue)){throw "Existing partial/output: $name"}}
$st=Get-Content -LiteralPath (Join-Path $job 'staging_status.json') -Raw -Encoding UTF8|ConvertFrom-Json
if($st.status -ne 'prepared_not_run'){throw 'Staging has not passed.'}
& (Join-Path $job 'verify_inputs.ps1') -ExpectedParametersSha256 $ExpectedParametersSha256 -ReceiptName 'r1_submit_verification.json'
$existing=Get-ScheduledTask -TaskName 'SAR20_MatlabControl' -ErrorAction Stop
if([string]$existing.State -ne 'Ready'){throw 'Original SAR20 task is not idle.'}
$p=@(Get-Process -Name MATLAB -ErrorAction Stop);if($p.Count -ne 1 -or $p[0].Id -ne 27628 -or -not $p[0].Responding){throw 'Expected one responsive GUI MATLAB PID 27628.'}
if(Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue){throw 'Task already exists.'}
$busy=@(Get-ScheduledTask|Where-Object{$_.TaskName -like 'SAR20*' -and [string]$_.State -eq 'Running'});if($busy.Count){throw 'Another SAR20 task is running.'}
$xml=Export-ScheduledTask -TaskName 'SAR20_MatlabControl';[IO.File]::WriteAllText((Join-Path $job 'recovery_task_before.xml'),$xml,[Text.UTF8Encoding]::new($false))
$arguments='-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "D:/Temp/SAR20NORMAL_20261104_NX/recovery_controller.ps1" -ExpectedParametersSha256 '+$ExpectedParametersSha256
$action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments -WorkingDirectory $job
Register-ScheduledTask -TaskName $taskName -Action $action -Principal $existing.Principal -Settings $existing.Settings|Out-Null
Start-ScheduledTask -TaskName $taskName
$r=@{status='submitted';task_name=$taskName;gui_pid=$p[0].Id;parameters_sha256=$ExpectedParametersSha256;execution_time_limit=[string]$existing.Settings.ExecutionTimeLimit}
[IO.File]::WriteAllText((Join-Path $job 'recovery_submission_receipt.json'),($r|ConvertTo-Json),[Text.UTF8Encoding]::new($false));$r|ConvertTo-Json -Compress
