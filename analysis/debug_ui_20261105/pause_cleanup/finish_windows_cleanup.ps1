# Resume cleanup after PowerShell's long-path Remove-Item failure; no goal work.
$ErrorActionPreference='Stop'
$job='D:\Temp\SAR20DEBUG_UI_20261105';$out=Join-Path $job 'pause_cleanup'
$p=@(Get-Process MATLAB)
if($p.Count -ne 1 -or $p[0].Id -ne 27628){throw 'Unexpected MATLAB worker.'}
$names=@('SAR20_CAAZ_AZVX_20261105','SAR20_CAAZ_UNIT_20261105','SAR20_DEBUG_CLASSIFY_20261105',
 'SAR20_DEBUG_DISPLAYPROP_20261105','SAR20_DEBUG_GRAPH1_20261105','SAR20_DEBUG_QUERY_20261105',
 'SAR20_DEBUG_SOURCE_SMOKE_20261105','SAR20_FRAME_BUILD_20261105','SAR20_PKU_CAAZ_N8_20261105',
 'SAR20_PKU_CICC_N8_20261105','SAR20_PKU_DEMOD_20261105','SAR20_PKU_PROBE_20261105','SAR20_DEBUG_PAUSE_CLEANUP_20261105')
foreach($n in $names){
 if(Get-ScheduledTask -TaskName $n -ErrorAction SilentlyContinue){throw ('Task unexpectedly still registered: '+$n)}
 if(-not (Test-Path -LiteralPath (Join-Path $out ($n+'.xml')))){throw ('Missing preserved definition: '+$n)}
}
$paths=@('D:\Temp\SAR20DEBUG_SOURCE_SMOKE_20261105\worker_prefs',
 'D:\Temp\SAR20DEBUG_GRAPH1_20261105\worker_prefs','D:\Temp\SAR20DEBUG_CLASSIFY_20261105\worker_prefs',
 'D:\Temp\SAR20_WORKER_TMP\DEBUG_SOURCE_SMOKE_20261105','D:\Temp\SAR20_WORKER_TMP\DEBUG_GRAPH1_20261105',
 'D:\Temp\SAR20_WORKER_TMP\DEBUG_CLASSIFY_20261105',
 'D:\Temp\SAR20DEBUG_SOURCE_SMOKE_20261105\slprj','D:\Temp\SAR20DEBUG_GRAPH1_20261105\slprj',
 'D:\Temp\SAR20DEBUG_CLASSIFY_20261105\slprj')
$rows=@();[long]$removedNow=0
foreach($path in $paths){
 if(-not (Test-Path -LiteralPath $path)){continue}
 $rootItem=Get-Item -LiteralPath $path
 if($rootItem.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Reparse root refused.'}
 $files=@(Get-ChildItem -LiteralPath $path -Recurse -Force)
 $unsafe=@($files|Where-Object {($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -or (-not $_.PSIsContainer -and $_.Length -gt 300000000)})
 if($unsafe.Count -gt 0){$rows += [pscustomobject]@{path=$path;status='skipped_large_or_reparse';bytes=0};continue}
 [long]$size=0;foreach($f in @($files|Where-Object {-not $_.PSIsContainer})){$size+=$f.Length}
 $extended='\\?\'+$path
 & cmd.exe /d /c ('rd /s /q "'+$extended+'"')
 if(Test-Path -LiteralPath $path){throw ('Extended-path cleanup failed: '+$path)}
 $removedNow+=$size;$rows += [pscustomobject]@{path=$path;status='deleted_regenerable';bytes=$size}
}
$model='D:\Academic\Projects\sar20m1\SAR20\current\models\SarAdc.slx'
if((Get-FileHash $model -Algorithm SHA256).Hash.ToLowerInvariant() -ne '91973cf76507d37acc12515b55ebfe731ad197fe8ca1ecc9014fa07cbd35c27e'){throw 'Original model changed.'}
$originals=@(Get-ScheduledTask -TaskName SAR20_MatlabControl,SAR20_ReadDesktop|Select-Object TaskName,State)
$r=[pscustomobject]@{status='PAUSE_CLEANUP_COMPLETE';retired_owned_tasks=$names.Count;definitions_preserved=$true;cache_cleanup=$rows;cache_logical_bytes_removed_in_recovery=$removedNow;previous_partial_cache_bytes_not_counted=$true;original_tasks=$originals;original_matlab_retained=$true;raw_and_as_run_preserved=$true;default_model_unchanged=$true}
[IO.File]::WriteAllText((Join-Path $out 'receipt.json'),($r|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
[pscustomobject]@{status=$r.status;retired_tasks=$names.Count;remaining_cache_bytes_removed=$removedNow;default_model_unchanged=$true}|ConvertTo-Json -Compress
