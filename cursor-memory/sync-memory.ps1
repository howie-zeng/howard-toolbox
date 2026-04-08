# sync-memory.ps1 - Sync Cursor memory files between S: canonical store and local workspaces.
# Runs bidirectional newer-wins. Designed for Task Scheduler (every 15 min, business hours).

$canonBase = "S:\QR\hzeng\howard-toolbox\cursor-memory"
$uncFallback = "\\libremax.com\dfs\shares\QR\hzeng\howard-toolbox\cursor-memory"
$logFile = Join-Path $canonBase "sync-memory.log"

# Resolve canonical base: prefer S: mapping, fall back to UNC
if (-not (Test-Path $canonBase)) {
    $canonBase = $uncFallback
    $logFile = Join-Path $canonBase "sync-memory.log"
    if (-not (Test-Path $canonBase)) {
        $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
        Add-Content $logFile "$ts WARN S: and UNC both unreachable - skipping"
        exit 0
    }
}

function Write-SyncLog($msg) {
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Add-Content $logFile "$ts $msg"
}

function Sync-FilePair($canon, $local) {
    $cExists = Test-Path $canon
    $lExists = Test-Path $local
    if (-not $cExists -and -not $lExists) { return }
    if ($cExists -and -not $lExists) {
        $dir = Split-Path $local -Parent
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        Copy-Item $canon $local -Force
        Write-SyncLog "SYNC canon -> $local (new file)"
        return
    }
    if (-not $cExists -and $lExists) {
        $dir = Split-Path $canon -Parent
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        Copy-Item $local $canon -Force
        Write-SyncLog "SYNC $local -> canon (new file)"
        return
    }
    $cTime = (Get-Item $canon).LastWriteTime
    $lTime = (Get-Item $local).LastWriteTime
    $diff = ($cTime - $lTime).TotalSeconds
    if ([Math]::Abs($diff) -le 2) { return }
    if ($diff -gt 0) {
        Copy-Item $canon $local -Force
        Write-SyncLog ('SYNC canon -> {0} (canon newer by {1}s)' -f $local, [int]$diff)
    } else {
        Copy-Item $local $canon -Force
        Write-SyncLog ('SYNC {0} -> canon (local newer by {1}s)' -f $local, [int][Math]::Abs($diff))
    }
}

function Sync-RulesDir($canonDir, $localDir) {
    $allFiles = @{}
    if (Test-Path $canonDir) {
        Get-ChildItem $canonDir -File | ForEach-Object { $allFiles[$_.Name] = $true }
    }
    if (Test-Path $localDir) {
        Get-ChildItem $localDir -File | ForEach-Object { $allFiles[$_.Name] = $true }
    }
    foreach ($name in $allFiles.Keys) {
        Sync-FilePair (Join-Path $canonDir $name) (Join-Path $localDir $name)
    }
}

# -- Project mappings (hardcoded; change annually at most) --

# LMQR: sync to primary clone only; 3 other clones are hardlinked on C:
Sync-FilePair "$canonBase\lmqr\AGENTS.md"  "C:\Git\LMQR\AGENTS.md"
Sync-RulesDir "$canonBase\lmqr\rules"      "C:\Git\LMQR\.cursor\rules"

# LMSim
Sync-FilePair "$canonBase\lmsim\AGENTS.md"  "C:\Git\LMSim\AGENTS.md"

# openclaw
Sync-RulesDir "$canonBase\openclaw\rules"   "C:\Git\.openclaw\.cursor\rules"

# howard-toolbox: canonical copy under cursor-memory/, workspace copy at repo root
Sync-FilePair "$canonBase\howard-toolbox\AGENTS.md"  "S:\QR\hzeng\howard-toolbox\AGENTS.md"
Sync-RulesDir "$canonBase\howard-toolbox\rules"      "S:\QR\hzeng\howard-toolbox\.cursor\rules"
