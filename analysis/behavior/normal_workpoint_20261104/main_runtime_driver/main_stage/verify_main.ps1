param([Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedManifestSha256,[ValidatePattern('^[A-Za-z0-9_]+\.json$')][string]$ReceiptName='main_source_verification.json')
$ErrorActionPreference='Stop';$job='D:\Temp\SAR20NORMAL_20261104_NX';$manifest=Join-Path $job 'main_manifest.json'
$r=@{status='verifying';error='';files=0;manifest_sha256=$ExpectedManifestSha256}
try {
 $item=Get-Item -LiteralPath $manifest -Force;if($item.Length -gt 300000000 -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Unsafe main manifest.'}
 if((Get-FileHash -LiteralPath $manifest -Algorithm SHA256).Hash -ne $ExpectedManifestSha256){throw 'Main manifest differs.'}
 $m=Get-Content -LiteralPath $manifest -Raw -Encoding UTF8|ConvertFrom-Json
 if($m.schema -ne 'sar20-normal-main-scratch/v1' -or @($m.items).Count -eq 0){throw 'Unexpected main manifest.'}
 foreach($e in $m.items){
  $rel=[string]$e.path;if($rel -match '(^/|\\|:|(^|/)\.{1,2}(/|$)|//)'){throw "Unsafe source path: $rel"}
  $f=Get-Item -LiteralPath (Join-Path $job ($rel.Replace('/','\'))) -Force
  if($f.PSIsContainer -or $f.Length -gt 300000000 -or ($f.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw "Unsafe source: $rel"}
  if($f.Length -ne $e.bytes -or (Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash -ne $e.sha256){throw "Source differs: $rel"}
  $r.files++
 }
 $r.status='verified_not_run'
}catch{$r.status='failed';$r.error=($_.Exception.ToString()+"`n"+$_.ScriptStackTrace)}
[IO.File]::WriteAllText((Join-Path $job $ReceiptName),($r|ConvertTo-Json),[Text.UTF8Encoding]::new($false));if($r.status -ne 'verified_not_run'){throw $r.error}
$r|ConvertTo-Json -Compress
