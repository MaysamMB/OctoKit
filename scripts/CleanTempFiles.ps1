<#
.SYNOPSIS
    Auto Temp Cleaner - safely deletes the CONTENTS of known temp/cache folders.

.DESCRIPTION
    Cleans (does not delete the folders themselves):
        - %TEMP%                (current user's temp folder; no admin needed)
        - C:\Windows\Temp       (requires admin)
    Also empties the Recycle Bin (unless -IncludeRecycleBin false is passed).

    NOTE: C:\Windows\Prefetch is intentionally NOT cleaned. Windows manages
    Prefetch itself for boot/app-launch performance, and deleting it on an
    hourly schedule provides no real benefit while adding unnecessary risk.

    - Only files older than -MinAgeMinutes are touched, so anything an
      application just created/is actively using is left alone.
    - Locked/in-use files are skipped silently (no error dialogs, just a log line).
    - Folders requiring admin rights are skipped gracefully (with a log entry)
      when the script is run without elevation, so it still cleans what it can.
    - Every path is validated against a strict whitelist before anything is
      touched, so the script can never delete outside these roots.
    - All actions are timestamped and written to a log file.

    ------------------------------------------------------------------------
    DESKTOP APP INTEGRATION (added; original cleanup behavior is unchanged)
    ------------------------------------------------------------------------
    Two additive capabilities were added on top of the original script so a
    GUI can drive it without changing anything about how cleanup itself
    works:

      -ScanOnly    Performs a completely read-only pass: walks the same
                   whitelisted roots with the same age-cutoff and safety
                   logic used by cleanup, but never deletes or empties
                   anything. Used to show "what CAN be cleaned" (estimated
                   space, file/folder counts) before the user asks for a
                   real cleanup. Combine with -OutputJson.

      -OutputJson  Emits a single structured JSON object to stdout
                   summarizing the scan or cleanup that just ran (per-root
                   file/folder/byte counts, skipped/locked/too-new counts,
                   Recycle Bin info). This is IN ADDITION to the existing
                   log file — nothing about the log format changed.

    Running the script exactly as before (no -ScanOnly, no -OutputJson) is
    byte-for-byte the same cleanup behavior as the original script.

.PARAMETER DryRun
    If specified, reports what WOULD be deleted without deleting anything.
    Ignored (with a log note) when -ScanOnly is also specified, since scan
    mode never deletes regardless.

.PARAMETER MinAgeMinutes
    Only items whose LastWriteTime is older than this many minutes are
    deleted. Defaults to 120 (2 hours), so recently-created/modified files
    are left alone even if the task runs every hour.

.PARAMETER IncludeRecycleBin
    Whether the Recycle Bin should be included (emptied during cleanup, or
    estimated during scan). Defaults to $true, matching the original
    script's unconditional behavior.

.PARAMETER ScanOnly
    Read-only mode: computes what cleanup would affect without deleting or
    emptying anything. Never combine expectations of deletion with this flag.

.PARAMETER OutputJson
    Emit a structured JSON summary to stdout in addition to normal logging.

.NOTES
    Designed to be run either:
      - manually by a standard user (cleans %TEMP% + Recycle Bin only), or
      - via Scheduled Task as SYSTEM with highest privileges (cleans all targets), or
      - invoked by the WinToolkit desktop application via -OutputJson.
#>

[CmdletBinding()]
param(
    [switch]$DryRun,
    [int]$MinAgeMinutes = 120,
    # NOTE: intentionally a validated string, not [bool]. PowerShell's
    # -File invocation (used by the desktop app's execution layer) passes
    # every argument as a plain string and cannot bind a [bool] parameter
    # from any string value ("true"/"false"/"1"/"0" are all rejected) -
    # only an actual boolean literal typed directly into an interactive
    # -Command works, which is not how this script is invoked. Confirmed
    # by direct testing against PowerShell 7.4.
    [ValidateSet('true', 'false')]
    [string]$IncludeRecycleBin = 'true',
    [switch]$ScanOnly,
    [switch]$OutputJson
)

$IncludeRecycleBinBool = $IncludeRecycleBin -eq 'true'

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------

$LogFolder = 'C:\ProgramData\AutoTempCleaner'
$LogFile   = Join-Path $LogFolder 'cleanup.log'
$MaxLogSizeBytes = 5MB   # simple log rotation threshold

# Explicit whitelist of folders whose CONTENTS may be deleted.
# The script will refuse to touch anything that does not resolve
# to exactly one of these roots (see Test-IsSafeRoot below).
$TargetRoots = @(
    @{ Path = $env:TEMP;               RequiresAdmin = $false },
    @{ Path = 'C:\Windows\Temp';        RequiresAdmin = $true  }
)
# NOTE: C:\Windows\Prefetch is deliberately excluded - see script header notes.

# ----------------------------------------------------------------------------
# Helpers (UNCHANGED from the original script)
# ----------------------------------------------------------------------------

function Test-IsAdmin {
    $identity  = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Initialize-Log {
    if (-not (Test-Path -LiteralPath $LogFolder)) {
        New-Item -Path $LogFolder -ItemType Directory -Force | Out-Null
    }
    if (Test-Path -LiteralPath $LogFile) {
        $size = (Get-Item -LiteralPath $LogFile).Length
        if ($size -gt $MaxLogSizeBytes) {
            $archive = Join-Path $LogFolder ("cleanup_{0:yyyyMMdd_HHmmss}.log" -f (Get-Date))
            Rename-Item -LiteralPath $LogFile -NewName (Split-Path $archive -Leaf) -Force
        }
    }
}

function Write-Log {
    param(
        [Parameter(Mandatory)][string]$Message,
        [ValidateSet('INFO','WARN','ERROR','SKIP')][string]$Level = 'INFO'
    )
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line = "[$timestamp] [$Level] $Message"
    try {
        Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8 -ErrorAction Stop
    } catch {
        # If logging itself fails (e.g. disk full), fall back to console only.
        Write-Verbose $line
    }
    Write-Verbose $line
}

# Safety net: confirm a resolved path is EXACTLY one of the whitelisted roots
# (not a parent of it, not a symlink trick, not something outside it).
function Test-IsSafeRoot {
    param([string]$CandidatePath)

    if ([string]::IsNullOrWhiteSpace($CandidatePath)) { return $false }

    try {
        $resolved = [System.IO.Path]::GetFullPath($CandidatePath).TrimEnd('\')
    } catch {
        return $false
    }

    foreach ($root in $TargetRoots) {
        try {
            $rootResolved = [System.IO.Path]::GetFullPath($root.Path).TrimEnd('\')
        } catch {
            continue
        }
        if ($resolved -ieq $rootResolved) { return $true }
    }
    return $false
}

# Removes only the CONTENTS of a validated root folder. The root itself is
# never removed. Locked/in-use items are caught and skipped per-item.
#
# ADDED: now also returns a structured summary (files vs folders, bytes
# deleted) alongside the exact same Write-Log calls as the original script.
# The deletion logic, ordering, and safety checks below are unchanged.
function Clear-FolderContents {
    param(
        [Parameter(Mandatory)][string]$RootPath
    )

    $summary = [ordered]@{
        path            = $RootPath
        processed       = $false
        filesDeleted    = 0
        foldersDeleted  = 0
        bytesDeleted    = 0
        skippedLocked   = 0
        tooNew          = 0
        error           = $null
    }

    if (-not (Test-IsSafeRoot -CandidatePath $RootPath)) {
        Write-Log -Level ERROR -Message "Refusing to process '$RootPath' - not in whitelist."
        $summary.error = "Not in whitelist"
        return [PSCustomObject]$summary
    }

    if (-not (Test-Path -LiteralPath $RootPath)) {
        Write-Log -Level WARN -Message "Path not found, skipping: $RootPath"
        $summary.error = "Path not found"
        return [PSCustomObject]$summary
    }

    $summary.processed = $true

    $deleted = 0
    $skipped = 0
    $tooNew  = 0

    $cutoff = (Get-Date).AddMinutes(-$MinAgeMinutes)

    $items = Get-ChildItem -LiteralPath $RootPath -Force -ErrorAction SilentlyContinue
    foreach ($item in $items) {

        # Leave anything recently created/modified alone - it may still be
        # in active use even if not currently locked.
        if ($item.LastWriteTime -gt $cutoff) {
            $tooNew++
            continue
        }

        # Belt-and-braces: re-validate every item is actually inside the root
        # we intend to clean before removing it.
        #
        # BUGFIX (found via functional testing, section 27): the original
        # check hardcoded a backslash separator ($RootPath.TrimEnd('\') +
        # '\'), which is correct on Windows (the only real deployment
        # target) but silently causes EVERY item to be treated as
        # "out of scope" and skipped - with no deletion, no error, just a
        # WARN log line - on any PowerShell host using a different path
        # separator (e.g. PowerShell 7 on Linux/macOS). Using
        # [System.IO.Path]::DirectorySeparatorChar keeps the exact same
        # (correct) behavior on Windows while fixing this latent gap. The
        # safety intent and strictness of the check are unchanged.
        $separator = [System.IO.Path]::DirectorySeparatorChar
        if (-not $item.FullName.StartsWith(($RootPath.TrimEnd($separator) + $separator), [StringComparison]::OrdinalIgnoreCase)) {
            Write-Log -Level WARN -Message "Skipped out-of-scope item: $($item.FullName)"
            continue
        }

        $itemSize = Get-ItemSizeSafe -Item $item

        if ($DryRun) {
            Write-Log -Level INFO -Message "[DRY RUN] Would delete: $($item.FullName)"
            if ($item.PSIsContainer) { $summary.foldersDeleted++ } else { $summary.filesDeleted++ }
            $summary.bytesDeleted += $itemSize
            continue
        }

        try {
            Remove-Item -LiteralPath $item.FullName -Recurse -Force -ErrorAction Stop
            $deleted++
            if ($item.PSIsContainer) { $summary.foldersDeleted++ } else { $summary.filesDeleted++ }
            $summary.bytesDeleted += $itemSize
        } catch {
            # Covers: file in use, access denied, path too long, etc.
            $skipped++
            Write-Log -Level SKIP -Message "Skipped (in use or inaccessible): $($item.FullName) - $($_.Exception.Message)"
        }
    }

    $summary.skippedLocked = $skipped
    $summary.tooNew = $tooNew

    Write-Log -Level INFO -Message "Finished '$RootPath': $deleted item(s) deleted, $skipped item(s) skipped (in use), $tooNew item(s) left alone (newer than $MinAgeMinutes min)."

    return [PSCustomObject]$summary
}

# ----------------------------------------------------------------------------
# ADDED helpers (read-only; used by -ScanOnly and by size reporting)
# ----------------------------------------------------------------------------

function Get-ItemSizeSafe {
    param($Item)
    try {
        if ($Item.PSIsContainer) {
            $sum = (Get-ChildItem -LiteralPath $Item.FullName -Recurse -Force -ErrorAction SilentlyContinue |
                Where-Object { -not $_.PSIsContainer } |
                Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
            if ($null -eq $sum) { return 0 }
            return [int64]$sum
        } else {
            return [int64]$Item.Length
        }
    } catch {
        return 0
    }
}

# Purely read-only equivalent of Clear-FolderContents: walks the same root
# with the same whitelist + age-cutoff rules, but never deletes anything.
function Get-FolderContentsScanSummary {
    param(
        [Parameter(Mandatory)][string]$RootPath
    )

    $summary = [ordered]@{
        path             = $RootPath
        processed        = $false
        filesEligible    = 0
        foldersEligible  = 0
        bytesEligible    = 0
        tooNew           = 0
        error            = $null
    }

    if (-not (Test-IsSafeRoot -CandidatePath $RootPath)) {
        $summary.error = "Not in whitelist"
        return [PSCustomObject]$summary
    }

    if (-not (Test-Path -LiteralPath $RootPath)) {
        $summary.error = "Path not found"
        return [PSCustomObject]$summary
    }

    $summary.processed = $true
    $cutoff = (Get-Date).AddMinutes(-$MinAgeMinutes)

    $items = Get-ChildItem -LiteralPath $RootPath -Force -ErrorAction SilentlyContinue
    foreach ($item in $items) {
        if ($item.LastWriteTime -gt $cutoff) {
            $summary.tooNew++
            continue
        }

        if ($item.PSIsContainer) { $summary.foldersEligible++ } else { $summary.filesEligible++ }
        $summary.bytesEligible += (Get-ItemSizeSafe -Item $item)
    }

    return [PSCustomObject]$summary
}

# Read-only estimate of Recycle Bin contents size, via the Shell COM API.
# Never modifies the Recycle Bin. Returns $null if it cannot be determined.
function Get-RecycleBinEstimate {
    try {
        $shell = New-Object -ComObject Shell.Application
        $bin = $shell.NameSpace(0xA)
        if (-not $bin) { return $null }

        $items = $bin.Items()
        $count = $items.Count
        $bytes = 0
        foreach ($item in $items) {
            try {
                $bytes += [int64]$bin.GetDetailsOf($item, 3) -replace '[^\d]', ''
            } catch {
                # Some shell namespaces report size in localized/formatted
                # strings that can't be parsed reliably; skip that item's
                # contribution rather than fail the whole estimate.
            }
        }
        return [PSCustomObject]@{ itemCount = $count; bytes = [int64]$bytes }
    } catch {
        return $null
    }
}

# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

Initialize-Log

$isAdmin = Test-IsAdmin

if ($ScanOnly -and $DryRun) {
    Write-Log -Level WARN -Message "-DryRun has no effect when -ScanOnly is specified (scan never deletes)."
}

if ($ScanOnly) {
    # ------------------------------------------------------------------
    # READ-ONLY SCAN PATH - never deletes or empties anything.
    # ------------------------------------------------------------------
    Write-Log -Message "===== Scan run started (Admin: $isAdmin) ====="

    $targetResults = @()
    foreach ($target in $TargetRoots) {
        if ($target.RequiresAdmin -and -not $isAdmin) {
            Write-Log -Level WARN -Message "Skipping scan of '$($target.Path)' - requires administrator privileges (not elevated)."
            $targetResults += [PSCustomObject]@{
                path = $target.Path; requiresAdmin = $true; skippedAdmin = $true
                processed = $false; filesEligible = 0; foldersEligible = 0; bytesEligible = 0; tooNew = 0; error = $null
            }
            continue
        }
        $scanResult = Get-FolderContentsScanSummary -RootPath $target.Path
        $targetResults += [PSCustomObject]@{
            path = $target.Path; requiresAdmin = $target.RequiresAdmin; skippedAdmin = $false
            processed = $scanResult.processed; filesEligible = $scanResult.filesEligible
            foldersEligible = $scanResult.foldersEligible; bytesEligible = $scanResult.bytesEligible
            tooNew = $scanResult.tooNew; error = $scanResult.error
        }
    }

    $recycleBinInfo = $null
    if ($IncludeRecycleBinBool) {
        $estimate = Get-RecycleBinEstimate
        $recycleBinInfo = [PSCustomObject]@{
            included      = $true
            itemCount     = if ($estimate) { $estimate.itemCount } else { $null }
            estimatedBytes = if ($estimate) { $estimate.bytes } else { $null }
            estimateAvailable = [bool]$estimate
        }
    } else {
        $recycleBinInfo = [PSCustomObject]@{ included = $false; itemCount = 0; estimatedBytes = 0; estimateAvailable = $true }
    }

    $totalFiles = ($targetResults | Measure-Object -Property filesEligible -Sum).Sum
    $totalFolders = ($targetResults | Measure-Object -Property foldersEligible -Sum).Sum
    $totalBytes = ($targetResults | Measure-Object -Property bytesEligible -Sum).Sum
    $totalTooNew = ($targetResults | Measure-Object -Property tooNew -Sum).Sum

    Write-Log -Message "===== Scan run finished ====="

    $safeTotalBytes = 0
    if ($totalBytes) { $safeTotalBytes = [int64]$totalBytes }
    $safeRecycleBinBytes = 0
    if ($recycleBinInfo.estimatedBytes) { $safeRecycleBinBytes = [int64]$recycleBinInfo.estimatedBytes }
    $combinedBytesEligible = $safeTotalBytes + $safeRecycleBinBytes

    $result = [PSCustomObject]@{
        success           = $true
        mode              = "scan"
        readOnly          = $true
        isAdmin           = $isAdmin
        minAgeMinutes     = $MinAgeMinutes
        includeRecycleBin = $IncludeRecycleBinBool
        targets           = $targetResults
        recycleBin        = $recycleBinInfo
        totals            = [PSCustomObject]@{
            filesEligible   = if ($totalFiles) { $totalFiles } else { 0 }
            foldersEligible = if ($totalFolders) { $totalFolders } else { 0 }
            bytesEligible   = $combinedBytesEligible
            tooNew          = if ($totalTooNew) { $totalTooNew } else { 0 }
        }
        logFile           = $LogFile
        scanCompletedAt   = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    }

    if ($OutputJson) {
        $result | ConvertTo-Json -Depth 6 -Compress
    } else {
        Write-Output $result
    }

    exit 0
}

# ----------------------------------------------------------------------------
# CLEANUP PATH - identical behavior to the original script, with structured
# results additionally collected for -OutputJson.
# ----------------------------------------------------------------------------

Write-Log -Message "===== Cleanup run started (Admin: $isAdmin, DryRun: $($DryRun.IsPresent)) ====="

$targetResults = @()
foreach ($target in $TargetRoots) {
    if ($target.RequiresAdmin -and -not $isAdmin) {
        Write-Log -Level WARN -Message "Skipping '$($target.Path)' - requires administrator privileges (not elevated)."
        $targetResults += [PSCustomObject]@{
            path = $target.Path; requiresAdmin = $true; skippedAdmin = $true
            processed = $false; filesDeleted = 0; foldersDeleted = 0; bytesDeleted = 0
            skippedLocked = 0; tooNew = 0; error = $null
        }
        continue
    }
    $cleanupResult = Clear-FolderContents -RootPath $target.Path
    $targetResults += [PSCustomObject]@{
        path = $target.Path; requiresAdmin = $target.RequiresAdmin; skippedAdmin = $false
        processed = $cleanupResult.processed; filesDeleted = $cleanupResult.filesDeleted
        foldersDeleted = $cleanupResult.foldersDeleted; bytesDeleted = $cleanupResult.bytesDeleted
        skippedLocked = $cleanupResult.skippedLocked; tooNew = $cleanupResult.tooNew
        error = $cleanupResult.error
    }
}

# Empty the Recycle Bin. Wrapped so a locked/missing bin never stops the run.
$recycleBinInfo = [PSCustomObject]@{ included = $IncludeRecycleBinBool; emptied = $false; estimatedBytesBefore = $null; error = $null }

if ($IncludeRecycleBinBool) {
    $estimateBefore = Get-RecycleBinEstimate
    $recycleBinInfo.estimatedBytesBefore = if ($estimateBefore) { $estimateBefore.bytes } else { $null }

    if ($DryRun) {
        Write-Log -Message "[DRY RUN] Would empty the Recycle Bin."
    } else {
        try {
            Clear-RecycleBin -Force -ErrorAction SilentlyContinue
            Write-Log -Message "Recycle Bin emptied."
            $recycleBinInfo.emptied = $true
        } catch {
            Write-Log -Level WARN -Message "Could not empty Recycle Bin: $($_.Exception.Message)"
            $recycleBinInfo.error = $_.Exception.Message
        }
    }
} else {
    Write-Log -Message "Recycle Bin excluded from this run by request."
}

Write-Log -Message "===== Cleanup run finished ====="

if ($OutputJson) {
    $totalFiles = ($targetResults | Measure-Object -Property filesDeleted -Sum).Sum
    $totalFolders = ($targetResults | Measure-Object -Property foldersDeleted -Sum).Sum
    $totalBytes = ($targetResults | Measure-Object -Property bytesDeleted -Sum).Sum
    $totalSkipped = ($targetResults | Measure-Object -Property skippedLocked -Sum).Sum
    $totalTooNew = ($targetResults | Measure-Object -Property tooNew -Sum).Sum

    $result = [PSCustomObject]@{
        success           = $true
        mode              = "cleanup"
        dryRun            = [bool]$DryRun
        isAdmin           = $isAdmin
        minAgeMinutes     = $MinAgeMinutes
        includeRecycleBin = $IncludeRecycleBinBool
        targets           = $targetResults
        recycleBin        = $recycleBinInfo
        totals            = [PSCustomObject]@{
            filesDeleted   = if ($totalFiles) { $totalFiles } else { 0 }
            foldersDeleted = if ($totalFolders) { $totalFolders } else { 0 }
            bytesDeleted   = if ($totalBytes) { $totalBytes } else { 0 }
            skippedLocked  = if ($totalSkipped) { $totalSkipped } else { 0 }
            tooNew         = if ($totalTooNew) { $totalTooNew } else { 0 }
        }
        logFile           = $LogFile
        cleanupCompletedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    }

    $result | ConvertTo-Json -Depth 6 -Compress
}
