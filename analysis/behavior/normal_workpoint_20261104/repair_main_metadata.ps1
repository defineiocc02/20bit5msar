$ErrorActionPreference='Stop'
$job='D:\Temp\SAR20NORMAL_20261104_NX'
$archive=Join-Path $job 'failed_preflight_1'
$payload=Join-Path $job 'metadata_repair_payload'
if(Test-Path -LiteralPath $archive){throw 'Failure archive already exists.'}
if(Test-Path -LiteralPath $payload){throw 'Repair payload already exists.'}
$state=Get-Content -LiteralPath (Join-Path $job 'main_controller_status.json') -Raw -Encoding UTF8|ConvertFrom-Json
$fail=Get-Content -LiteralPath (Join-Path $job 'ideal_v2_n8\failed.json') -Raw -Encoding UTF8|ConvertFrom-Json
if($state.status -ne 'failed' -or $state.completed.Count -ne 0 -or $fail.id -ne 'normalCase:index' -or $fail.simout_saved){throw 'Expected pre-simulation metadata failure only.'}
$p=@(Get-Process -Name MATLAB -ErrorAction Stop)
if($p.Count -ne 1 -or $p[0].Id -ne 27628 -or -not $p[0].Responding){throw 'Expected only original GUI MATLAB.'}
$task=Get-ScheduledTask -TaskName 'SAR20_NORMAL_MAIN_20261104_NX'
if([string]$task.State -eq 'Running'){throw 'Main task still running.'}
if((Get-FileHash -LiteralPath (Join-Path $job 'main.zip') -Algorithm SHA256).Hash -ne 'd3c069e5499a8b86ad65149b53360002c57ef101e6c12e10d4f1fce2b2a7d524'){throw 'Original main ZIP differs.'}
if((Get-FileHash -LiteralPath (Join-Path $job 'main_manifest.json') -Algorithm SHA256).Hash -ne 'b7d95ee1777b2d0197d98d97a2b472cc86dfeea36cb8a65bbcb0217b866cc703'){throw 'Original main manifest differs.'}
$zip=Join-Path $job 'main_metadata_repair.zip'
if((Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash -ne '0cc3a1c87604383ac52af7cc3b0e42ece84b92835a88c3a979df23eebeb95c49'){throw 'Repair ZIP differs.'}
Expand-Archive -LiteralPath $zip -DestinationPath $payload
$stage=Join-Path $payload 'main_stage';$manifest=Join-Path $stage 'main_manifest.json'
if((Get-FileHash -LiteralPath $manifest -Algorithm SHA256).Hash -ne '5736786be7676739dd5b48f71f5662f357b394354d0d2b0855e38478576f761f'){throw 'Repair manifest differs.'}
$m=Get-Content -LiteralPath $manifest -Raw -Encoding UTF8|ConvertFrom-Json
foreach($e in $m.items){$f=Get-Item -LiteralPath (Join-Path $stage $e.path) -Force;if($f.Length -gt 300000000 -or ($f.Attributes -band [IO.FileAttributes]::ReparsePoint) -or $f.Length -ne $e.bytes -or (Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash -ne $e.sha256){throw 'Invalid repair payload.'}}
$names=@('ideal_v2_n8','ideal_v2_n8_tmp','ideal_v2_n8_prefs','ideal_v2_n8_wrapper.json','ideal_v2_n8.lock','ideal_v2_n8_stdout.log','ideal_v2_n8_stderr.log','main_execution.lock','main_controller_status.json','main_submission_receipt.json','main_existing_task_before.xml','main_existing_task_after.xml')
foreach($n in $names){$f=Get-Item -LiteralPath (Join-Path $job $n) -Force;if($f.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Reparse in failed attempt.'};$files=@($f);if($f.PSIsContainer){$files=@(Get-ChildItem -LiteralPath $f.FullName -File -Recurse -Force)};foreach($x in $files){if($x.Length -gt 300000000){throw 'Oversized failed-attempt file; no move allowed.'}}}
[void](New-Item -ItemType Directory -Path $archive)
Copy-Item -LiteralPath (Join-Path $job 'main.zip'),(Join-Path $job 'main_manifest.json'),(Join-Path $job 'normal_main_controller.ps1'),(Join-Path $job 'scripts\normal_case.m') -Destination $archive
$xml=Export-ScheduledTask -TaskName 'SAR20_NORMAL_MAIN_20261104_NX'
[IO.File]::WriteAllText((Join-Path $archive 'owned_task_definition.xml'),$xml,[Text.UTF8Encoding]::new($false))
foreach($f in @(Get-ChildItem -LiteralPath $job -File -Filter 'main_*.json')){if($names -notcontains $f.Name){Copy-Item -LiteralPath $f.FullName -Destination $archive -Force}}
foreach($n in $names){Move-Item -LiteralPath (Join-Path $job $n) -Destination (Join-Path $archive $n)}
Copy-Item -LiteralPath (Join-Path $stage 'scripts\normal_case.m') -Destination (Join-Path $job 'scripts\normal_case.m') -Force
Copy-Item -LiteralPath $manifest -Destination (Join-Path $job 'main_manifest.json') -Force
Copy-Item -LiteralPath $zip -Destination (Join-Path $job 'main.zip') -Force
& (Join-Path $job 'verify_main.ps1') -ExpectedManifestSha256 '5736786be7676739dd5b48f71f5662f357b394354d0d2b0855e38478576f761f' -ReceiptName 'metadata_repair_verification.json'
Unregister-ScheduledTask -TaskName 'SAR20_NORMAL_MAIN_20261104_NX' -Confirm:$false
$r=@{status='repaired_not_run';reason='Correct a mistyped 62-character runtime-index hash to the independently verified 64-character hash.';archive=$archive;physics_source_changed=$false;model_changed=$false;P_changed=$false;seed_changed=$false}
[IO.File]::WriteAllText((Join-Path $job 'metadata_repair_receipt.json'),($r|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
$r|ConvertTo-Json -Compress
