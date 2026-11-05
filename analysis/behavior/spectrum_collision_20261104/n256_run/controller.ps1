$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$dir = 'D:\Temp\SAR20N256_20261104_qfhxXr'
$status = Join-Path $dir 'controller_status.json'
$log = Join-Path $dir 'controller.log'
$stage = 'start'
$app = $null
function Log([string]$s) {
    [IO.File]::AppendAllText($log, (Get-Date).ToUniversalTime().ToString('o') + ' ' + $s + "`n", [Text.UTF8Encoding]::new($false))
}
function State([string]$s, [string]$details) {
    $v = @{ status=$s; stage=$stage; detail=$details; utc=(Get-Date).ToUniversalTime().ToString('o') }
    [IO.File]::WriteAllText($status, (ConvertTo-Json $v -Compress) + "`n", [Text.UTF8Encoding]::new($false))
    Log ($s + ': ' + $details)
}
try {
    $stage = 'attach'
    $app = [Runtime.InteropServices.Marshal]::GetActiveObject('Matlab.Application')
    $probe = [string]$app.Execute("fprintf(1,'SAR20_FFT_PID:%d\n',feature('getpid'));")
    if ($probe -notmatch 'SAR20_FFT_PID:(\d+)') { throw ('MATLAB PID marker missing: ' + $probe) }
    $observedPid = [int]$Matches[1]
    if ($observedPid -ne 27628) { throw ('MATLAB PID mismatch: ' + $observedPid) }
    State 'attached' $probe
    $stage = 'matlab_entry'
    $reply = [string]$app.Execute("run('D:/Temp/SAR20N256_20261104_qfhxXr/sar20_n256_entry_20261104.m');")
    State 'returned_check_matlab_receipt' $reply
} catch {
    State 'controller_failed' $_.Exception.Message
    exit 1
} finally {
    if ($null -ne $app) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app); Log 'COM reference released; MATLAB remains open.' }
}
