#requires -Version 7.0
<##
Preview is the default. Run -Apply only while the ETS workflow is idle.
Deletes individual reviewed copies, never directories. Historical runtime
preparations become incomplete and must be re-prepared before being launched.
All their receipts, maps, native overlays and compiled source/stage inputs remain.
##>
[CmdletBinding(SupportsShouldProcess, ConfirmImpact='Medium')]
param(
    [switch]$Apply,
    [switch]$VerifyContent,
    [ValidateSet('Both','C','D')][string]$Drive = 'Both',
    [string]$Manifest = 'D:\knx_analysis\disk-cleanup-2026-10-18\manifest.json'
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$ExpectedManifestHash = 'E3E8CBC4C83A474491941D3D667525391F8A564C6A8ED1B44A4E6FBE1E24CCD2'
$Manifest = [IO.Path]::GetFullPath($Manifest)
if ((Get-FileHash -LiteralPath $Manifest).Hash -ne $ExpectedManifestHash) { throw 'Reviewed manifest changed. Do not apply an unreviewed plan.' }
$plan = Get-Content -LiteralPath $Manifest -Raw | ConvertFrom-Json
$base = Split-Path -Parent $Manifest
if ((Get-FileHash -LiteralPath $plan.FileList.Path).Hash -ne $plan.FileList.Sha256) { throw 'Reviewed file list changed.' }
$groups = @{}
foreach ($group in $plan.Groups) { $groups[$group.Root] = $group }
$checkedParents = @{}
$hashCache = @{}
$statePin = $plan.Authority | Where-Object Path -eq 'D:\knx_analysis\STATE.json'
$cursorPath = (Get-Content -LiteralPath $statePin.Path -Raw | ConvertFrom-Json).Naming.BlockCursor
$cursorPin = $plan.Authority | Where-Object Path -eq $cursorPath

function Assert-NoLinks([string]$path) {
    $part = [IO.Path]::GetFullPath($path)
    while ($part) {
        if (!$checkedParents.ContainsKey($part) -and (Test-Path -LiteralPath $part)) {
            if ((Get-Item -LiteralPath $part -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Linked path refused: $part" }
            $checkedParents[$part] = $true
        }
        $parent = [IO.Path]::GetDirectoryName($part)
        if ($parent -eq $part) { break }
        $part = $parent
    }
}
function Assert-State {
    if ((Get-FileHash -LiteralPath $statePin.Path).Hash -ne $statePin.Sha256) { throw 'STATE changed after this plan was reviewed. Re-audit; do not bypass the pin.' }
    if (!$cursorPin -or (Get-FileHash -LiteralPath $cursorPin.Path).Hash -ne $cursorPin.Sha256) { throw 'Current cursor changed after this plan was reviewed. Re-audit before cleanup.' }
}
function Assert-Quiet {
    Assert-State
    $state = Get-Content -LiteralPath $statePin.Path -Raw | ConvertFrom-Json
    $cursor = Get-Content -LiteralPath $state.Naming.BlockCursor -Raw | ConvertFrom-Json
    if (@($cursor.Running).Count -or @($cursor.IndependentRunning).Count -or $cursor.RestoreRequired) { throw 'Owned work or restoration is pending. Preserve it and stop cleanup.' }
    $processes = @(Get-CimInstance Win32_Process)
    $ancestors = [Collections.Generic.HashSet[int]]::new()
    $next = $PID
    while ($next -and $ancestors.Add($next)) {
        $parent = $processes | Where-Object ProcessId -eq $next | Select-Object -First 1
        if (!$parent) { break }
        $next = [int]$parent.ParentProcessId
    }
    foreach ($process in $processes) {
        if ($ancestors.Contains([int]$process.ProcessId)) { continue }
        $command = ('' + $process.CommandLine + ' ' + $process.ExecutablePath).Replace('/','\')
        $producer = $process.Name -match '^(python.*|dotnet|MSBuild|ETS6.*|dnSpy.*|NameCandidates|pwsh|powershell)\.exe$'
        if ($producer -and ($command -match '(?i)D:\\knx_analysis\\|C:\\Users\\tony\\\.codex\\worktrees\\ets-disposition-workflow\\')) {
            throw "Workflow process is running: $($process.Name), PID $($process.ProcessId). Stop/pause its owning task before manual cleanup."
        }
    }
}
function Hash-Cached([string]$path) {
    Assert-NoLinks $path
    $file = Get-Item -LiteralPath $path -Force
    $key = $path + '|' + $file.Length + '|' + $file.LastWriteTimeUtc.Ticks
    if (!$hashCache.ContainsKey($key)) { $hashCache[$key] = (Get-FileHash -LiteralPath $path).Hash }
    return $hashCache[$key]
}
function Check-File($row) {
    $path = [IO.Path]::GetFullPath($row.Path)
    $root = [IO.Path]::GetFullPath($row.Root).TrimEnd('\')
    if (!$groups.ContainsKey($root) -or !$path.StartsWith($root + '\',[StringComparison]::OrdinalIgnoreCase)) { throw "Path outside reviewed group: $path" }
    if ([IO.Path]::GetExtension($path) -notin @('.dll','.exe')) { throw "Non-binary refused: $path" }
    if ($row.Kind -eq 'OldPerformanceStage') {
        if ($root -notmatch '^D:\\knx_analysis\\(?:perfprobe\\stage64-v\d+|perfcheck2\\apply-v\d+|perfcheck3\\wave\d+)$') { throw 'Invalid performance stage root' }
    } elseif ($row.Kind -eq 'SupersededRuntimeCopy') {
        if ($root -notmatch '^C:\\Users\\tony\\\.codex\\worktrees\\ets-disposition-workflow\\ets64-v(\d+)(?:-expanded112|-combined)?-runtime(?:-prepared)?01\\live$' -or [int]$Matches[1] -lt 190 -or [int]$Matches[1] -gt 214) { throw 'Invalid superseded runtime root' }
        $counterpart = [IO.Path]::GetFullPath($row.Counterpart)
        if ($counterpart.StartsWith($root + '\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Retained counterpart is inside cleanup tree' }
        Assert-NoLinks $counterpart
        if (!(Test-Path -LiteralPath $counterpart -PathType Leaf) -or (Get-Item -LiteralPath $counterpart).Length -ne $row.Length) { throw "Retained counterpart missing or changed: $counterpart" }
        if (($Apply -or $VerifyContent) -and (Hash-Cached $counterpart) -ne $row.Sha256) { throw "Retained counterpart changed: $counterpart" }
    } else { throw 'Unknown cleanup kind' }
    Assert-NoLinks $path
    if (!(Test-Path -LiteralPath $path)) { return $null }
    $file = Get-Item -LiteralPath $path -Force
    if ($file.PSIsContainer -or ($file.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw "Non-regular file: $path" }
    if ($file.Length -ne $row.Length -or $file.LastWriteTimeUtc.Ticks -ne $row.WriteTicks) { throw "Reviewed file changed: $path" }
    if ($row.Kind -eq 'SupersededRuntimeCopy' -and ($Apply -or $VerifyContent) -and (Hash-Cached $path) -ne $row.Sha256) { throw "Runtime copy changed: $path" }
    return $file
}

Assert-Quiet
foreach ($pin in $plan.Authority) {
    Assert-NoLinks $pin.Path
    if ((Get-FileHash -LiteralPath $pin.Path).Hash -ne $pin.Sha256) { throw "Authority changed: $($pin.Path)" }
}
foreach ($group in $plan.Groups) {
    Assert-NoLinks $group.Root
    if ($group.Kind -eq 'SupersededRuntimeCopy') {
        foreach ($pin in @($group.Provenance,$group.Binding)) {
            if ((Get-FileHash -LiteralPath $pin.Path).Hash -ne $pin.Sha256) { throw "Runtime evidence changed: $($pin.Path)" }
        }
    }
}
$preview = Join-Path $base ('preview-' + $Drive + '.csv')
$writer = [IO.StreamWriter]::new($preview,$false,[Text.UTF8Encoding]::new($false))
$counts = @{ C = [long]0; D = [long]0 }; $bytes = @{ C = [long]0; D = [long]0 }; $missing = 0
try {
    $writer.WriteLine('Path,LogicalBytes,Kind,RetainedCounterpart')
    foreach ($line in [IO.File]::ReadLines($plan.FileList.Path)) {
        $row = $line | ConvertFrom-Json
        $volume = $row.Path.Substring(0,1)
        if ($Drive -ne 'Both' -and $Drive -ne $volume) { continue }
        $file = Check-File $row
        if (!$file) { $missing++; continue }
        $counts[$volume]++; $bytes[$volume] += $file.Length
        if (($counts.C + $counts.D) % 2000 -eq 0) { Write-Host "Checked $($counts.C + $counts.D) candidate files..." }
        $counterpart = if ($row.Kind -eq 'SupersededRuntimeCopy') { $row.Counterpart } else { '' }
        $writer.WriteLine(('"{0}",{1},"{2}","{3}"' -f $row.Path,$file.Length,$row.Kind,$counterpart))
    }
} finally { $writer.Dispose() }
Assert-Quiet
foreach ($volume in @('C','D')) {
    Write-Host ('{0}: {1:N0} files; {2:N2} GiB logical candidates' -f $volume,$counts[$volume],($bytes[$volume]/1GB))
}
Write-Host "Verified listing: $preview. Already absent: $missing. Compression/hard links reduce actual space recovered."
if (!$Apply) { Write-Host 'PREVIEW ONLY: nothing deleted. Metadata/evidence checked; -Apply always checks C: copy/counterpart SHA256 before deletion. Use -VerifyContent for a full hash preview.'; return }
foreach ($pin in $plan.Authority) {
    if ((Get-FileHash -LiteralPath $pin.Path).Hash -ne $pin.Sha256) { throw "Authority changed during preview: $($pin.Path)" }
}
if (!$PSCmdlet.ShouldProcess("$($counts.C + $counts.D) verified individual copies",'Permanently delete')) { return }

$logPath = Join-Path $base ('deleted-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.jsonl')
$log = [IO.StreamWriter]::new($logPath,$false,[Text.UTF8Encoding]::new($false))
$before = @{}; foreach ($v in @('C','D')) { $before[$v] = ([IO.DriveInfo]::new($v + ':\')).AvailableFreeSpace }
$lastRoot = ''; $deleted = 0
try {
    foreach ($line in [IO.File]::ReadLines($plan.FileList.Path)) {
        $row = $line | ConvertFrom-Json
        if ($Drive -ne 'Both' -and $Drive -ne $row.Path.Substring(0,1)) { continue }
        if ($lastRoot -ne $row.Root) {
            Assert-Quiet
            $checkedParents.Clear()
            $lastRoot = $row.Root
        }
        if ($deleted % 128 -eq 0) { Assert-State }
        $file = Check-File $row
        if (!$file) { continue }
        # No recursive deletion and no directory removal. The path was resolved,
        # contained, link-checked and identity-checked immediately above.
        Remove-Item -LiteralPath $file.FullName -ErrorAction Stop
        $log.WriteLine(($row | ConvertTo-Json -Compress)); $log.Flush()
        $deleted++
        if ($deleted % 2000 -eq 0) { Write-Host "Deleted $deleted verified copies..." }
    }
} finally {
    $log.Dispose()
    foreach ($v in @('C','D')) {
        $after = ([IO.DriveInfo]::new($v + ':\')).AvailableFreeSpace
        Write-Host ('{0}: free {1:N2} GiB; observed change {2:N2} GiB' -f $v,($after/1GB),(($after-$before[$v])/1GB))
    }
    Write-Host "Deleted $deleted files. Audit: $logPath"
}
