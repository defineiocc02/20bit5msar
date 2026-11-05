param([Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedParametersSha256,[ValidatePattern('^[A-Za-z0-9_]+\.json$')][string]$ReceiptName='initial_verification.json')
$ErrorActionPreference='Stop';$job='D:\Temp\SAR20NORMAL_20261104_NX'
$r=@{status='verifying';error='';candidate_files=0;baseline_files=0;range_files=0}
function Check([string]$path,[string]$hash){$f=Get-Item -LiteralPath $path -Force;if($f.PSIsContainer -or $f.Length -gt 300000000 -or ($f.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw "Unsafe file: $path"};$d=$f.Directory;while($null -ne $d){if($d.Attributes -band [IO.FileAttributes]::ReparsePoint){throw "Reparse: $($d.FullName)"};if([string]::Equals($d.FullName,$job,[StringComparison]::OrdinalIgnoreCase)){break};$d=$d.Parent};if($null -eq $d){throw "Outside job: $path"};if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $hash){throw "Hash differs: $path"}}
try{
 Check (Join-Path $job 'merged.zip') '03545ad4ea5e228511f379c690fe83c43123deed5612f6a664ef8b98275560b4'
 Check (Join-Path $job 'range.zip') '1b06d6dad4c6ffc0a67220c213ff097def3877ed16bb475370e0c1f7d029bb28'
 Check (Join-Path $job 'normal_parameters.m') $ExpectedParametersSha256
 Check (Join-Path $job 'scripts\normal_gate.m') '059080c7205eac2aa54e3955b8aa433be40cdbc32a59007282bb04c067bdd8f2'
 Check (Join-Path $job 'scripts\normal_profile.m') 'ad3e1170b42b132fbf9b3b949fb3e0de17e94f7161028731bbf79733555cb2d3'
 Check (Join-Path $job 'scripts\normal_jobroot.m') '2495bfe17d85f31b8ae572c79ee4ad2673e16c8a6d87f216c52315411530ded5'
 Check (Join-Path $job 'reference\sb256_same_bits.m') 'd4e7faf5b72d581be895cdfa5f3a6bf51b17e882df792fc78e6322c498b7e527'
 Check (Join-Path $job 'inputs\P_used.mat') '236ddfb427dfc07e7f7e27dd58746deb30946891717d255b53789aa8127a1e9f'
 Check (Join-Path $job 'model\SarAdc.slx') '48537818b3212e1e4c8231dec433d1fde36d95814cdcce8c529bb2898eb097d3'
 $c=Join-Path $job 'candidate\MANIFEST.json';Check $c '73867eabe50b70920cd3373190832e2d78426c59b0116d6062ff94c4c903f14c';$cm=Get-Content -LiteralPath $c -Raw -Encoding UTF8|ConvertFrom-Json
 if($cm.schema -ne 'sar20-merged-single-ou-az-dac-rc-ktc-cmp/v1'){throw 'Wrong candidate schema.'}
 foreach($e in @($cm.files.PSObject.Properties)){$rel=([string]$e.Name).Replace('/','\');Check (Join-Path (Join-Path $job 'candidate') $rel) $e.Value;$r.candidate_files++}
 if($r.candidate_files -ne 134){throw 'Wrong candidate count.'}
 $b=Join-Path $job 'baseline\single_bank\MANIFEST.json';Check $b '2cbdffe537b694cef6107ce893ea8bca7f8ef5d95f6ff7d993f020150c6dd514';$bm=Get-Content -LiteralPath $b -Raw -Encoding UTF8|ConvertFrom-Json
 foreach($e in $bm.items){$rel=([string]$e.path).Replace('/','\');Check (Join-Path (Join-Path $job 'baseline\single_bank') $rel) $e.sha256;$r.baseline_files++}
 if($r.baseline_files -ne 117){throw 'Wrong baseline count.'}
 $h=Join-Path $job 'range_helpers\MANIFEST.json';Check $h 'a8cfc6db345fc80f96b9cbaeadbb1f1cc44b73c6cf45938e98f4b771c8d176cc';$hm=Get-Content -LiteralPath $h -Raw -Encoding UTF8|ConvertFrom-Json
 foreach($e in $hm.items){$rel=([string]$e.path).Replace('/','\');Check (Join-Path (Join-Path $job 'range_helpers') $rel) $e.sha256;$r.range_files++}
 if($r.range_files -ne 8){throw 'Wrong range count.'}
 $r.status='verified_not_run'
}catch{$r.status='failed';$r.error=($_.Exception.ToString()+"`n"+$_.ScriptStackTrace)}
[IO.File]::WriteAllText((Join-Path $job $ReceiptName),($r|ConvertTo-Json -Depth 6),[Text.UTF8Encoding]::new($false));if($r.status -ne 'verified_not_run'){throw $r.error}
$r|ConvertTo-Json -Compress
