param([Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedZipSha256,[Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedManifestSha256)
$ErrorActionPreference='Stop';$job='D:\Temp\SAR20NORMAL_20261104_NX';$zip=Join-Path $job 'main.zip';$stage=Join-Path $job 'main_stage'
foreach($d in @('D:\Temp',$job)){ $i=Get-Item -LiteralPath $d -Force;if(-not $i.PSIsContainer -or ($i.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw "Unsafe directory: $d"} }
foreach($p in @($stage,(Join-Path $job 'main_manifest.json'),(Join-Path $job 'main_staging_status.json'))){if($null -ne (Get-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue)){throw "Existing staging path: $p"}}
$r=@{status='starting';error='';files=0}
try{
 $i=Get-Item -LiteralPath $zip -Force;if($i.Length -gt 300000000 -or ($i.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Unsafe ZIP.'}
 if((Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash -ne $ExpectedZipSha256){throw 'Main ZIP differs.'}
 Expand-Archive -LiteralPath $zip -DestinationPath $job
 $mf=Join-Path $stage 'main_manifest.json';$i=Get-Item -LiteralPath $mf;if($i.Length -gt 300000000 -or (Get-FileHash -LiteralPath $mf -Algorithm SHA256).Hash -ne $ExpectedManifestSha256){throw 'Main manifest differs.'}
 $m=Get-Content -LiteralPath $mf -Raw -Encoding UTF8|ConvertFrom-Json;if($m.schema -ne 'sar20-normal-main-scratch/v1'){throw 'Unexpected main schema.'}
 foreach($e in $m.items){
  $rel=[string]$e.path;if($rel -match '(^/|\\|:|(^|/)\.{1,2}(/|$)|//)'){throw "Unsafe item: $rel"}
  $src=Join-Path $stage ($rel.Replace('/','\'));$i=Get-Item -LiteralPath $src -Force
  if($i.Length -gt 300000000 -or ($i.Attributes -band [IO.FileAttributes]::ReparsePoint) -or $i.Length -ne $e.bytes -or (Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash -ne $e.sha256){throw "Staged source differs: $rel"}
  $dst=Join-Path $job ($rel.Replace('/','\'));$existing=Get-Item -LiteralPath $dst -Force -ErrorAction SilentlyContinue
  if($null -ne $existing){if($existing.PSIsContainer -or ($existing.Attributes -band [IO.FileAttributes]::ReparsePoint) -or $existing.Length -gt 300000000 -or (Get-FileHash -LiteralPath $dst -Algorithm SHA256).Hash -ne $e.sha256){throw "Existing destination differs: $rel"}}
  else{$parent=Split-Path -Parent $dst;if(-not (Test-Path -LiteralPath $parent)){[void](New-Item -ItemType Directory -Path $parent -Force)};Copy-Item -LiteralPath $src -Destination $dst -ErrorAction Stop}
  $r.files++
 }
 Copy-Item -LiteralPath $mf -Destination (Join-Path $job 'main_manifest.json') -ErrorAction Stop
 & (Join-Path $job 'verify_main.ps1') -ExpectedManifestSha256 $ExpectedManifestSha256 -ReceiptName 'main_initial_verification.json'
 $r.status='prepared_not_run'
}catch{$r.status='failed';$r.error=($_.Exception.ToString()+"`n"+$_.ScriptStackTrace)}
[IO.File]::WriteAllText((Join-Path $job 'main_staging_status.json'),($r|ConvertTo-Json),[Text.UTF8Encoding]::new($false));if($r.status -ne 'prepared_not_run'){throw $r.error}
$r|ConvertTo-Json -Compress
