param([Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedParametersSha256,[Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedMainManifestSha256)
$ErrorActionPreference='Stop';$job='D:\Temp\SAR20NORMAL_20261104_NX';$taskName='SAR20_NORMAL_MAIN_20261104_NX'
foreach($dir in @('D:\Temp',$job)){ $i=Get-Item -LiteralPath $dir -Force;if(-not $i.PSIsContainer -or ($i.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw "Unsafe directory: $dir"} }
foreach($name in @('main_execution.lock','main_controller_status.json','ideal_v2_n8','ideal_merged_n8','normal_merged_n8','normal_merged_n8_tap','ideal_merged_n256','normal_merged_n256')){if($null -ne (Get-Item -LiteralPath (Join-Path $job $name) -Force -ErrorAction SilentlyContinue)){throw "Existing partial/output: $name"}}
function Read-Small([string]$file){$i=Get-Item -LiteralPath $file -Force;if($i.PSIsContainer -or $i.Length -gt 300000000 -or ($i.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw "Unsafe receipt: $file"};return (Get-Content -LiteralPath $file -Raw -Encoding UTF8|ConvertFrom-Json)}
$p=Read-Small (Join-Path $job 'profile\complete.json')
if($p.status -ne 'prepared' -or $p.candidate_manifest_sha256 -ne '73867eabe50b70920cd3373190832e2d78426c59b0116d6062ff94c4c903f14c'){throw 'Merged profile has not passed.'}
foreach($name in @('test_single_rc_ktc','test_joint_ou_az_dac','test_joint_ou_rc_return','test_comparator_single','test_normal_10v')){
 $folder=Join-Path (Join-Path $job 'gates') $name;$g=Read-Small (Join-Path $folder 'complete.json');$want=if($name -eq 'test_normal_10v'){'FUNCTION_ASSERTIONS_PASSED'}else{'passed'}
 if($g.status -ne $want -or $g.test -ne $name -or $g.candidate_manifest_sha256 -ne $p.candidate_manifest_sha256 -or $g.pid -eq 27628 -or $g.model_loaded){throw "Gate not valid: $name"}
 $mat=Get-Item -LiteralPath (Join-Path $folder 'report.mat') -Force;if($mat.Length -gt 300000000 -or ($mat.Attributes -band [IO.FileAttributes]::ReparsePoint) -or (Get-FileHash -LiteralPath $mat.FullName -Algorithm SHA256).Hash -ne $g.report_sha256){throw "Gate report differs: $name"}
}
foreach($pair in @(@('profile\ideal_P.mat',$p.ideal_P_sha256),@('profile\normal_P.mat',$p.normal_P_sha256))){$mat=Get-Item -LiteralPath (Join-Path $job $pair[0]) -Force;if($mat.Length -gt 300000000 -or ($mat.Attributes -band [IO.FileAttributes]::ReparsePoint) -or (Get-FileHash -LiteralPath $mat.FullName -Algorithm SHA256).Hash -ne $pair[1]){throw "Profile P differs: $($pair[0])"}}
& (Join-Path $job 'verify_inputs.ps1') -ExpectedParametersSha256 $ExpectedParametersSha256 -ReceiptName 'main_submit_inputs.json'
& (Join-Path $job 'verify_main.ps1') -ExpectedManifestSha256 $ExpectedMainManifestSha256 -ReceiptName 'main_submit_sources.json'
$existing=Get-ScheduledTask -TaskName 'SAR20_MatlabControl' -ErrorAction Stop
if([string]$existing.State -ne 'Ready'){throw 'Original SAR20 task is not idle.'}
$mat=@(Get-Process -Name MATLAB -ErrorAction Stop);if($mat.Count -ne 1 -or $mat[0].Id -ne 27628 -or -not $mat[0].Responding){throw 'Expected one responsive GUI MATLAB PID 27628.'}
if(Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue){throw 'Task already exists.'}
$busy=@(Get-ScheduledTask|Where-Object{$_.TaskName -like 'SAR20*' -and [string]$_.State -eq 'Running'});if($busy.Count){throw 'Another SAR20 task is running.'}
$xml=Export-ScheduledTask -TaskName 'SAR20_MatlabControl';[IO.File]::WriteAllText((Join-Path $job 'main_existing_task_before.xml'),$xml,[Text.UTF8Encoding]::new($false))
$arguments='-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "D:/Temp/SAR20NORMAL_20261104_NX/normal_main_controller.ps1" -ExpectedParametersSha256 '+$ExpectedParametersSha256+' -ExpectedMainManifestSha256 '+$ExpectedMainManifestSha256
$action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments -WorkingDirectory $job
Register-ScheduledTask -TaskName $taskName -Action $action -Principal $existing.Principal -Settings $existing.Settings|Out-Null
Start-ScheduledTask -TaskName $taskName
$r=@{status='submitted';task_name=$taskName;gui_pid=$mat[0].Id;parameters_sha256=$ExpectedParametersSha256;main_manifest_sha256=$ExpectedMainManifestSha256;execution_time_limit=[string]$existing.Settings.ExecutionTimeLimit}
[IO.File]::WriteAllText((Join-Path $job 'main_submission_receipt.json'),($r|ConvertTo-Json),[Text.UTF8Encoding]::new($false));$r|ConvertTo-Json -Compress
