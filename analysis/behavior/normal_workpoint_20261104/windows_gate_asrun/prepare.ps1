param([Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedParametersSha256)
$ErrorActionPreference='Stop';$job='D:\Temp\SAR20NORMAL_20261104_NX';$old='D:\Temp\SAR20SBN8_20261104'
function Check([string]$p,[string]$h){$i=Get-Item -LiteralPath $p -Force;if($i.PSIsContainer -or $i.Length -gt 300000000 -or ($i.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw "Unsafe: $p"};if((Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash -ne $h){throw "Hash differs: $p"}}
foreach($n in @('candidate','baseline','range_helpers','normal_10v','inputs','model','staging_status.json')){if($null -ne (Get-Item -LiteralPath (Join-Path $job $n) -Force -ErrorAction SilentlyContinue)){throw "Existing staging item: $n"}}
$r=@{status='starting';error=''}
try{
 Check (Join-Path $job 'merged.zip') '03545ad4ea5e228511f379c690fe83c43123deed5612f6a664ef8b98275560b4'
 Check (Join-Path $job 'range.zip') '1b06d6dad4c6ffc0a67220c213ff097def3877ed16bb475370e0c1f7d029bb28'
 Check (Join-Path $job 'normal_parameters.m') $ExpectedParametersSha256
 Expand-Archive -LiteralPath (Join-Path $job 'merged.zip') -DestinationPath $job
 Expand-Archive -LiteralPath (Join-Path $job 'range.zip') -DestinationPath $job
 Rename-Item -LiteralPath (Join-Path $job 'normal_10v') -NewName 'range_helpers'
 $p=Join-Path $old 'plain\P_used.mat';$model=Join-Path $old 'runtime\current\models\SarAdc.slx'
 Check $p '236ddfb427dfc07e7f7e27dd58746deb30946891717d255b53789aa8127a1e9f'
 Check $model '48537818b3212e1e4c8231dec433d1fde36d95814cdcce8c529bb2898eb097d3'
 [void](New-Item -ItemType Directory -Path (Join-Path $job 'inputs'),(Join-Path $job 'model') -ErrorAction Stop)
 Copy-Item -LiteralPath $p -Destination (Join-Path $job 'inputs\P_used.mat') -ErrorAction Stop
 Copy-Item -LiteralPath $model -Destination (Join-Path $job 'model\SarAdc.slx') -ErrorAction Stop
 & (Join-Path $job 'verify_inputs.ps1') -ExpectedParametersSha256 $ExpectedParametersSha256 -ReceiptName 'initial_verification.json'
 $r.status='prepared_not_run'
}catch{$r.status='failed';$r.error=($_.Exception.ToString()+"`n"+$_.ScriptStackTrace)}
[IO.File]::WriteAllText((Join-Path $job 'staging_status.json'),($r|ConvertTo-Json),[Text.UTF8Encoding]::new($false));if($r.status -ne 'prepared_not_run'){throw $r.error}
$r|ConvertTo-Json -Compress
