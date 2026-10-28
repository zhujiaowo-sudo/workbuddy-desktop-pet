param([Parameter(Mandatory=$true)][string]$PlanPath)
$ErrorActionPreference = 'Stop'
$plan = Get-Content -LiteralPath $PlanPath -Raw -Encoding UTF8 | ConvertFrom-Json
$work = [IO.Path]::GetFullPath((Split-Path -Parent $PlanPath))
$target = [IO.Path]::GetFullPath($plan.target)
$stage = [IO.Path]::GetFullPath($plan.stage)
$backup = [IO.Path]::GetFullPath($plan.backup)
$rootPath = [IO.Path]::GetFullPath($plan.root)
$exeName = 'WorkBuddyDesktopPet.exe'
$moved = $false
$installed = $false
$newProcess = $null
$validated = $false
function Save-Result([string]$state) {
    $result = @{state=$state;at=[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()}
    $result | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $rootPath 'update-result.json') -Encoding UTF8
}
function Start-Pet {
    Start-Process -FilePath (Join-Path $target $exeName) -ArgumentList $plan.arguments -WorkingDirectory $target -WindowStyle Hidden -PassThru
}
try {
    if ($plan.schema -ne 1 -or (Split-Path -Leaf $work) -notmatch '^\.workbuddy-update-[\w-]+$' -or
        (Split-Path -Parent $work) -ne (Split-Path -Parent $target) -or $stage -ne (Join-Path $work 'payload') -or
        (Split-Path -Parent $backup) -ne (Split-Path -Parent $target) -or
        (Split-Path -Leaf $backup) -notlike ((Split-Path -Leaf $target)+'.previous-*') -or
        $rootPath -eq $target -or $rootPath.StartsWith($target+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid plan paths' }
    foreach ($path in @($target,$stage,$rootPath,$work)) {
        $item=Get-Item -LiteralPath $path
        while ($null -ne $item) {
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse path' }
            $item=$item.Parent
        }
    }
    if (Test-Path -LiteralPath $backup) { throw 'Backup already exists' }
    $actual=@(Get-ChildItem -LiteralPath $stage -Recurse -Force)
    if (@($actual | Where-Object {$_.Attributes -band [IO.FileAttributes]::ReparsePoint}).Count) { throw 'Reparse entry' }
    $files=@($actual | Where-Object {-not $_.PSIsContainer})
    if ($files.Count -ne @($plan.files.PSObject.Properties).Count) { throw 'Stage file count changed' }
    foreach ($file in $files) {
        $relative=$file.FullName.Substring($stage.Length+1).Replace('\','/')
        $expected=$plan.files.PSObject.Properties[$relative]
        $hasher=[Security.Cryptography.SHA256]::Create()
        $stream=[IO.File]::OpenRead($file.FullName)
        try { $hash=[BitConverter]::ToString($hasher.ComputeHash($stream)).Replace('-','').ToLowerInvariant() }
        finally { $stream.Dispose();$hasher.Dispose() }
        if ($null -eq $expected -or $hash -ne $expected.Value) { throw 'Stage checksum changed' }
    }
    $current=Get-Process -Id $plan.pid -ErrorAction SilentlyContinue
    if ($current -and $current.Path -ne (Join-Path $target $exeName)) { throw 'Process does not match installation' }
    $validated=$true
    [IO.File]::WriteAllText((Join-Path $work 'helper-ready'),'ready')
    if ($current -and -not $current.WaitForExit(90000)) { throw 'Application still running' }
    # Another profile may use the same installation; never replace its loaded files.
    foreach ($other in @(Get-Process -Name 'WorkBuddyDesktopPet' -ErrorAction SilentlyContinue)) {
        if ($other.Path -eq (Join-Path $target $exeName)) { throw 'Another instance still running' }
    }
    Move-Item -LiteralPath $target -Destination $backup
    $moved=$true
    Move-Item -LiteralPath $stage -Destination $target
    $installed=$true
    $began=[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    $newProcess=Start-Pet
    $ready=$false
    for ($i=0;$i -lt 100;$i++) {
        Start-Sleep -Milliseconds 250
        try {
            $runtime=Get-Content -LiteralPath (Join-Path $rootPath 'runtime.json') -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($runtime.version -eq $plan.version -and $runtime.at -ge $began) { $ready=$true;break }
        } catch {}
        $newProcess.Refresh()
        if ($newProcess.HasExited) { break }
    }
    if (-not $ready) { throw 'Updated application did not become ready' }
    Save-Result 'success'
} catch {
    try {
        if ($installed) {
            if ($newProcess -and -not $newProcess.HasExited) { $newProcess.Kill();$newProcess.WaitForExit(5000) | Out-Null }
            Move-Item -LiteralPath $target -Destination (Join-Path $work 'failed-payload')
        }
        if ($moved) { Move-Item -LiteralPath $backup -Destination $target }
        Save-Result 'failed'
        if ($moved) { Start-Pet | Out-Null }
        elseif ($validated -and -not @(Get-Process -Name 'WorkBuddyDesktopPet' -ErrorAction SilentlyContinue | Where-Object {$_.Path -eq (Join-Path $target $exeName)}).Count) { Start-Pet | Out-Null }
    } catch { try { Save-Result 'restore_failed' } catch {} }
    exit 1
}
