param([Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedParametersSha256,[Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedMainManifestSha256)
$ErrorActionPreference='Stop'
$job='D:\Temp\SAR20NORMAL_20261104_NX';$exe='D:\Academic\Matlab\bin\matlab.exe'
$r=@{status='starting';phase='lock';error='';completed=@();startup_option='-softwareopengl';exit_code=$null;gui_preserved=$null;original_task_unchanged=$null}
$owns=$false;$guiStart=$null;$exitCode=1
function State { [IO.File]::WriteAllText((Join-Path $job 'main_controller_status.json'),($r|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false)) }
function Check-GUI {
    $p=@(Get-Process -Name MATLAB -ErrorAction Stop)
    if ($p.Count -ne 1 -or $p[0].Id -ne 27628 -or -not $p[0].Responding) { throw 'Expected one responsive GUI MATLAB PID 27628.' }
    $start=$p[0].StartTime.ToUniversalTime().ToString('o')
    if ($null -ne $script:guiStart -and $start -ne $script:guiStart) { throw 'GUI start time changed.' }
    return $start
}
foreach($dir in @('D:\Temp',$job)) {
    $info=Get-Item -LiteralPath $dir -Force
    if (-not $info.PSIsContainer -or ($info.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw "Unsafe temporary directory: $dir" }
}
try {
    $lock=[IO.File]::Open((Join-Path $job 'main_execution.lock'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
    $lock.Dispose();$owns=$true;State
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw 'MATLAB unavailable.' }
    $guiStart=Check-GUI
    $pairs=@(
        @{phase='ideal_v2_n8';output='ideal_v2_n8'},@{phase='ideal_merged_n8';output='ideal_merged_n8'},
        @{phase='normal_merged_n8';output='normal_merged_n8'},@{phase='normal_merged_n8_tap';output='normal_merged_n8_tap'},
        @{phase='normal_merged_n256';output='normal_merged_n256'},@{phase='ideal_merged_n256';output='ideal_merged_n256'}
    )
    foreach($pair in $pairs) {
        $phase=$pair.phase;$r.phase=$phase+'_preflight';State
        & (Join-Path $job 'verify_inputs.ps1') -ExpectedParametersSha256 $ExpectedParametersSha256 -ReceiptName ('main_verify_'+$phase+'.json')
        & (Join-Path $job 'verify_main.ps1') -ExpectedManifestSha256 $ExpectedMainManifestSha256 -ReceiptName ('main_sources_'+$phase+'.json')
        $free=(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory
        if ($free -lt 6000000) { throw 'Less than 6 GB physical memory available.' }
        [void](Check-GUI)
        if ($null -ne (Get-Item -LiteralPath (Join-Path $job $pair.output) -Force -ErrorAction SilentlyContinue)) { throw "Existing phase output: $($pair.output)" }
        $stageLock=[IO.File]::Open((Join-Path $job ($phase+'.lock')),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read);$stageLock.Dispose()
        $tmp=Join-Path $job ($phase+'_tmp');$pref=Join-Path $job ($phase+'_prefs')
        [void](New-Item -ItemType Directory -Path $tmp,$pref -ErrorAction Stop)
        $env:TEMP=$tmp;$env:TMP=$tmp;$env:MATLAB_PREFDIR=$pref;$env:MATLABPATH='';$env:SAR20_NORMAL_CASE=$phase
        $matlabArgs='-wait -softwareopengl -batch "run(''D:/Temp/SAR20NORMAL_20261104_NX/normal_main_entry.m'')"'
        $r.status='running';$r.phase=$phase;$r.exit_code=$null;State
        $child=Start-Process -FilePath $exe -ArgumentList $matlabArgs -WorkingDirectory $job -WindowStyle Hidden -PassThru -Wait `
            -RedirectStandardOutput (Join-Path $job ($phase+'_stdout.log')) -RedirectStandardError (Join-Path $job ($phase+'_stderr.log'))
        $r.exit_code=$child.ExitCode
        $r.phase=$phase+'_postverify';State
        & (Join-Path $job 'verify_inputs.ps1') -ExpectedParametersSha256 $ExpectedParametersSha256 -ReceiptName ('main_post_'+$phase+'.json')
        & (Join-Path $job 'verify_main.ps1') -ExpectedManifestSha256 $ExpectedMainManifestSha256 -ReceiptName ('main_sources_post_'+$phase+'.json')
        if ($child.ExitCode -ne 0) { throw "$phase exited with code $($child.ExitCode); inspect logs and partial outputs." }
        $receipt=Join-Path $job ($phase+'_wrapper.json');$item=Get-Item -LiteralPath $receipt
        if ($item.Length -gt 300000000) { throw 'Wrapper receipt exceeds 300 MB.' }
        $m=Get-Content -LiteralPath $receipt -Raw -Encoding UTF8|ConvertFrom-Json
        if ($m.status -ne 'passed' -or $m.phase -ne $phase) { throw "$phase did not pass." }
        $r.completed+=@($phase);State;[void](Check-GUI)
    }
    $r.status='passed';$r.phase='postcheck';$exitCode=0
} catch {
    if (-not $owns) { throw }
    $r.status='failed';$r.error=($_.Exception.ToString()+"`n"+$_.ScriptStackTrace);$exitCode=1
} finally {
    if ($owns) {
        if ($null -ne $guiStart) {
            try { [void](Check-GUI);$r.gui_preserved=$true }
            catch { $r.gui_preserved=$false;$r.status='failed';$r.error+="`nGUI postcheck: "+$_.Exception.ToString();$exitCode=1 }
        }
        try {
            $xml=Export-ScheduledTask -TaskName 'SAR20_MatlabControl';$after=Join-Path $job 'main_existing_task_after.xml'
            [IO.File]::WriteAllText($after,$xml,[Text.UTF8Encoding]::new($false))
            $r.original_task_unchanged=((Get-FileHash -LiteralPath $after -Algorithm SHA256).Hash -eq (Get-FileHash -LiteralPath (Join-Path $job 'main_existing_task_before.xml') -Algorithm SHA256).Hash)
            if (-not $r.original_task_unchanged) { throw 'Original task definition changed.' }
        } catch { $r.status='failed';$r.error+="`nTask postcheck: "+$_.Exception.ToString();$exitCode=1 }
        if ($exitCode -eq 0) { $r.phase='complete' };State
    }
}
exit $exitCode
