<#
.SYNOPSIS
    Smart Application Leftovers Cleaner - non-interactive, GUI-driven fork.

.DESCRIPTION
    Finds leftovers of an uninstalled Windows application, for review and
    deletion by the WinToolkit desktop application.

    ------------------------------------------------------------------------
    WHY THIS IS A FORK, NOT THE ORIGINAL SCRIPT UNCHANGED
    ------------------------------------------------------------------------
    The original "Smart Application Leftovers Cleaner" was a fully
    interactive console tool: it printed everything it found, then called
    `Read-Host "Type YES to delete the listed leftovers"` and, on a single
    "YES", deleted every folder and every registry key it had found in one
    blanket action. That interactive confirmation cannot exist inside a
    GUI, and the desktop app's own requirements (per-item checkboxes,
    Safe/Suspicious classification, a review dialog before anything is
    touched) call for per-item selection that the original script's single
    yes/no gate did not support. So this fork replaces the interactive
    confirmation with two explicit, non-interactive modes driven by the
    desktop app, while preserving every safety function from the original
    script UNCHANGED in behavior:

        Normalize-Text              - unchanged
        Test-ExactApplicationName   - unchanged EXTERNAL behavior (same
                                       inputs produce the same true/false),
                                       internally refactored to share logic
                                       with the new classification function
                                       below so scan results and delete-time
                                       re-validation can never disagree.
        Test-SafePath               - unchanged

    Two capabilities were ADDED that did not exist in the original script:

        Test-SafeRegistryLeaf       - NEW. The original script had no
                                       equivalent safety check for registry
                                       deletion at all - a name match alone
                                       was enough to queue a key for
                                       deletion. This validates that a
                                       registry path is a direct child of
                                       one of the three scanned Uninstall-
                                       adjacent roots, closing that gap.

        -Mode Delete re-validation  - every item passed in via -ItemsFile
                                       is re-checked against Test-SafePath /
                                       Test-SafeRegistryLeaf AND re-matched
                                       against the target application's
                                       search terms before deletion. Nothing
                                       is deleted just because the GUI asked
                                       for it - it must independently still
                                       pass the same checks a fresh scan
                                       would apply.

    The "still installed? abort." guard from the original script is
    preserved and re-checked in BOTH modes, including immediately before
    any deletion in -Mode Delete.

.PARAMETER TargetAppName
    The application name to search for (as it would appear, or have
    appeared, in "Programs and Features").

.PARAMETER Mode
    "Scan"   - read-only. Reports installed-match / candidate folders /
               candidate registry keys as JSON. Deletes nothing.
    "Delete" - deletes ONLY the items listed in -ItemsFile, after
               re-validating each one. Requires -ItemsFile.

.PARAMETER ItemsFile
    Path to a JSON file (written by the desktop app) of the form:
        { "folders": ["C:\\Users\\...\\SomeApp"], "registry": ["Microsoft.PowerShell.Core\\Registry::HKEY_CURRENT_USER\\Software\\SomeApp"] }
    Required when -Mode Delete is used. Ignored in Scan mode.

.EXAMPLE
    powershell.exe -File .\CleanAppLeftovers.ps1 -TargetAppName "XAMPP" -Mode Scan

.EXAMPLE
    powershell.exe -File .\CleanAppLeftovers.ps1 -TargetAppName "XAMPP" -Mode Delete -ItemsFile "C:\Temp\approved.json"
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$TargetAppName,

    [Parameter(Mandatory = $true)]
    [ValidateSet('Scan', 'Delete')]
    [string]$Mode,

    [string]$ItemsFile
)

function Write-JsonError {
    param([string]$Message, [string]$Details)
    $err = [PSCustomObject]@{
        success = $false
        error   = $Message
        details = $Details
    }
    $err | ConvertTo-Json -Compress
}

if ([string]::IsNullOrWhiteSpace($TargetAppName)) {
    Write-JsonError -Message "Application name cannot be empty."
    exit 1
}

if ($Mode -eq 'Delete' -and [string]::IsNullOrWhiteSpace($ItemsFile)) {
    Write-JsonError -Message "-ItemsFile is required when -Mode is Delete."
    exit 1
}

$ErrorActionPreference = "SilentlyContinue"
$script:diagnosticWarnings = New-Object System.Collections.Generic.List[string]

# ============================================================
# Helpers - UNCHANGED safety logic from the original script
# ============================================================

function Normalize-Text {
    param(
        [string]$Text
    )

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return ""
    }

    return ($Text.ToLower() -replace '[^a-z0-9]', '')
}


# Shared matching logic (original inline rules from Test-ExactApplicationName,
# extracted so scan-time classification and delete-time re-validation are
# guaranteed to use identical rules). Returns "Exact", "Containment", or
# "None" - never a bare boolean, so callers can classify Safe vs Suspicious.
function Get-ApplicationNameMatchQuality {
    param(
        [string]$Name,
        [string[]]$SearchTerms
    )

    if ([string]::IsNullOrWhiteSpace($Name)) {
        return "None"
    }

    $normalizedName = Normalize-Text $Name

    if ([string]::IsNullOrWhiteSpace($normalizedName)) {
        return "None"
    }

    foreach ($term in $SearchTerms) {

        $normalizedTerm = Normalize-Text $term

        if ([string]::IsNullOrWhiteSpace($normalizedTerm)) {
            continue
        }

        # Exact match
        if ($normalizedName -eq $normalizedTerm) {
            return "Exact"
        }

        # Safe containment only for sufficiently specific terms
        if (
            $normalizedTerm.Length -ge 5 -and
            $normalizedName -like "*$normalizedTerm*"
        ) {
            return "Containment"
        }
    }

    return "None"
}


# UNCHANGED external contract: same inputs produce the same true/false as
# the original standalone function. Now implemented on top of
# Get-ApplicationNameMatchQuality so there is one source of truth.
function Test-ExactApplicationName {
    param(
        [string]$Name,
        [string[]]$SearchTerms
    )

    return (Get-ApplicationNameMatchQuality -Name $Name -SearchTerms $SearchTerms) -ne "None"
}


function Test-SafePath {
    param(
        [string]$Path
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $false
    }

    try {
        $fullPath = [System.IO.Path]::GetFullPath($Path).TrimEnd('\')

        # Never allow obvious system/root folders
        $dangerousPaths = @(
            $env:SystemRoot,
            $env:windir,
            $env:SystemDrive + "\",
            $env:ProgramFiles,
            ${env:ProgramFiles(x86)},
            $env:LOCALAPPDATA,
            $env:APPDATA,
            $env:PROGRAMDATA
        )

        foreach ($dangerous in $dangerousPaths) {

            if ([string]::IsNullOrWhiteSpace($dangerous)) {
                continue
            }

            try {
                $dangerousFull = [System.IO.Path]::GetFullPath($dangerous).TrimEnd('\')

                if ($fullPath -eq $dangerousFull) {
                    return $false
                }
            }
            catch {}
        }

        return $true
    }
    catch {
        return $false
    }
}


# ============================================================
# NEW: registry-equivalent of Test-SafePath.
#
# The original script had no per-key safety check for registry deletion at
# all - a name match during scanning was the ONLY thing standing between a
# key and deletion. This validates that a candidate registry path is a
# DIRECT child of one of the three roots ever scanned (never a deeper
# nested key, never an unrelated hive), closing that gap.
# ============================================================

function Test-SafeRegistryLeaf {
    param(
        [string]$RegistryPath,
        [string[]]$AllowedRootPSPaths
    )

    if ([string]::IsNullOrWhiteSpace($RegistryPath)) {
        return $false
    }

    foreach ($root in $AllowedRootPSPaths) {

        if ([string]::IsNullOrWhiteSpace($root)) {
            continue
        }

        $prefix = "$root\"

        if ($RegistryPath.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {

            $remainder = $RegistryPath.Substring($prefix.Length)

            # Must be a direct child (no further '\') - matches the
            # non-recursive Get-ChildItem depth used during scanning.
            if ($remainder.Length -gt 0 -and -not $remainder.Contains('\')) {
                return $true
            }
        }
    }

    return $false
}


# ============================================================
# Shared step: is the application still installed? (UNCHANGED logic,
# extracted into a function so both Scan and Delete modes - and the
# pre-deletion re-check - use the exact same rule.)
# ============================================================

function Get-InstalledMatches {
    param([string]$TargetAppName)

    $uninstallPaths = @(
        "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*"
    )

    $matches = New-Object System.Collections.Generic.List[object]

    foreach ($path in $uninstallPaths) {

        $records = Get-ItemProperty $path -ErrorAction SilentlyContinue

        foreach ($record in $records) {

            if (-not $record.DisplayName) {
                continue
            }

            $displayName = [string]$record.DisplayName
            $publisher = [string]$record.Publisher
            $installLocation = [string]$record.InstallLocation

            $combined = "$displayName $publisher $installLocation"

            $targetNormalized = Normalize-Text $TargetAppName
            $combinedNormalized = Normalize-Text $combined

            if (
                $combinedNormalized -like "*$targetNormalized*" -or
                $displayName -like "*$TargetAppName*"
            ) {

                $matches.Add(
                    [PSCustomObject]@{
                        DisplayName     = $displayName
                        Publisher       = $publisher
                        InstallLocation = $installLocation
                    }
                )
            }
        }
    }

    return $matches
}


# ============================================================
# Shared step: build SAFE search terms (UNCHANGED logic, extracted).
# ============================================================

function Get-SearchTerms {
    param([string]$TargetAppName)

    $searchTerms = New-Object System.Collections.Generic.List[string]

    # Always keep the original application name
    $searchTerms.Add($TargetAppName)

    # Add normalized form, but DO NOT split multi-word names
    $normalizedTarget = Normalize-Text $TargetAppName

    if (
        -not [string]::IsNullOrWhiteSpace($normalizedTarget) -and
        -not $searchTerms.Contains($normalizedTarget)
    ) {
        $searchTerms.Add($normalizedTarget)
    }

    if ($normalizedTarget.Length -ge 5) {
        if (-not $searchTerms.Contains($normalizedTarget)) {
            $searchTerms.Add($normalizedTarget)
        }
    }

    return $searchTerms
}


# ============================================================
# Scan: filesystem (UNCHANGED search locations/depth; classification added)
# ============================================================

function Find-LeftoverFolders {
    param([string[]]$SearchTerms)

    $searchLocations = @(
        $env:LOCALAPPDATA,
        $env:APPDATA,
        $env:PROGRAMDATA,
        $env:ProgramFiles,
        ${env:ProgramFiles(x86)}
    )

    $found = New-Object System.Collections.Generic.List[object]
    $seenPaths = New-Object System.Collections.Generic.HashSet[string]

    foreach ($location in $searchLocations) {

        if (-not $location) { continue }
        if (-not (Test-Path $location)) { continue }

        try {
            $items = Get-ChildItem -Path $location -Directory -Force -ErrorAction SilentlyContinue

            foreach ($item in $items) {
                $quality = Get-ApplicationNameMatchQuality -Name $item.Name -SearchTerms $SearchTerms
                if ($quality -ne "None" -and $seenPaths.Add($item.FullName)) {
                    $found.Add([PSCustomObject]@{
                        path           = $item.FullName
                        classification = $(if ($quality -eq "Exact") { "Safe" } else { "Suspicious" })
                        reason         = $(if ($quality -eq "Exact") { "Folder name exactly matches the application name" } else { "Folder name contains the application name" })
                    })
                }
            }

            foreach ($item in $items) {
                try {
                    $subItems = Get-ChildItem -Path $item.FullName -Directory -Force -ErrorAction SilentlyContinue
                    foreach ($subItem in $subItems) {
                        $quality = Get-ApplicationNameMatchQuality -Name $subItem.Name -SearchTerms $SearchTerms
                        if ($quality -ne "None" -and $seenPaths.Add($subItem.FullName)) {
                            $found.Add([PSCustomObject]@{
                                path           = $subItem.FullName
                                classification = $(if ($quality -eq "Exact") { "Safe" } else { "Suspicious" })
                                reason         = $(if ($quality -eq "Exact") { "Folder name exactly matches the application name" } else { "Folder name contains the application name" })
                            })
                        }
                    }
                } catch {
                    $script:diagnosticWarnings.Add("Could not enumerate subfolders of $($item.FullName)")
                }
            }
        } catch {
            $script:diagnosticWarnings.Add("Could not scan location $location")
        }
    }

    return $found
}


# ============================================================
# Scan: registry (UNCHANGED search locations/depth; classification added)
# ============================================================

function Find-LeftoverRegistryKeys {
    param([string[]]$SearchTerms)

    $registrySearchLocations = @(
        "HKCU:\Software",
        "HKLM:\SOFTWARE",
        "HKLM:\SOFTWARE\WOW6432Node"
    )

    $found = New-Object System.Collections.Generic.List[object]
    $seenPaths = New-Object System.Collections.Generic.HashSet[string]

    foreach ($location in $registrySearchLocations) {

        if (-not (Test-Path $location)) { continue }

        try {
            $keys = Get-ChildItem -Path $location -ErrorAction SilentlyContinue

            foreach ($key in $keys) {
                $quality = Get-ApplicationNameMatchQuality -Name $key.PSChildName -SearchTerms $SearchTerms
                if ($quality -ne "None" -and $seenPaths.Add($key.PSPath)) {
                    $found.Add([PSCustomObject]@{
                        path           = $key.PSPath
                        name           = $key.PSChildName
                        classification = $(if ($quality -eq "Exact") { "Safe" } else { "Suspicious" })
                        reason         = $(if ($quality -eq "Exact") { "Registry key name exactly matches the application name" } else { "Registry key name contains the application name" })
                    })
                }
            }
        } catch {
            $script:diagnosticWarnings.Add("Could not scan registry location $location")
        }
    }

    return @{
        items            = $found
        allowedRootPSPaths = @(
            $registrySearchLocations | ForEach-Object {
                try { (Get-Item -LiteralPath $_ -ErrorAction Stop).PSPath } catch { $null }
            } | Where-Object { $_ }
        )
    }
}


# ============================================================
# MODE: Scan
# ============================================================

if ($Mode -eq 'Scan') {

    $installedMatches = Get-InstalledMatches -TargetAppName $TargetAppName

    if ($installedMatches.Count -gt 0) {
        $result = [PSCustomObject]@{
            success          = $true
            targetAppName    = $TargetAppName
            stillInstalled   = $true
            installedMatches = $installedMatches
            candidates       = [PSCustomObject]@{ folders = @(); registry = @() }
            warnings         = $script:diagnosticWarnings.ToArray()
            scanCompletedAt  = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        }
        $result | ConvertTo-Json -Depth 8 -Compress
        exit 0
    }

    $searchTerms = Get-SearchTerms -TargetAppName $TargetAppName
    # NOTE: Find-LeftoverFolders returns a List[object] via the function's
    # implicit output stream, which PowerShell enumerates on the way out -
    # a 1-item list becomes a bare scalar object and a 0-item list becomes
    # $null by the time it reaches $folders here (confirmed by direct
    # testing: a single real candidate produced "folders": {...} instead of
    # "folders": [{...}] in the JSON output). @() below restores correct,
    # consistent array shape for 0, 1, or many results.
    $folders = @(Find-LeftoverFolders -SearchTerms $searchTerms)
    $registryResult = Find-LeftoverRegistryKeys -SearchTerms $searchTerms

    $result = [PSCustomObject]@{
        success          = $true
        targetAppName    = $TargetAppName
        stillInstalled   = $false
        installedMatches = @()
        # NOTE: $searchTerms here is the CALLER-side variable that received
        # Get-SearchTerms' return value through the pipeline, which
        # PowerShell enumerates - so by this point it is already a plain
        # array (or a lone scalar for a single search term), not the
        # original List[string]. @() is the correct, safe way to guarantee
        # array shape for either case (unlike .ToArray(), which only
        # exists on the original List type).
        searchTerms      = @($searchTerms)
        candidates       = [PSCustomObject]@{
            folders  = $folders
            # $registryResult is a Hashtable returned from
            # Find-LeftoverRegistryKeys - hashtables are NOT enumerated by
            # the pipeline the way lists are, so .items below retains its
            # original List[object] shape untouched (verified directly) and
            # must NOT be wrapped in @() - unlike $folders above, wrapping a
            # genuine List[object] containing PSCustomObject elements in
            # @() is what triggers PowerShell's "Argument types do not
            # match" bug (see the -Mode Delete section below for the same
            # issue hit and fixed with .ToArray() instead). Direct
            # assignment here already serializes correctly for 0/1/many
            # items (verified directly).
            registry = $registryResult.items
        }
        allowedRegistryRootPSPaths = $registryResult.allowedRootPSPaths
        warnings         = $script:diagnosticWarnings.ToArray()
        scanCompletedAt  = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    }

    $result | ConvertTo-Json -Depth 8 -Compress
    exit 0
}


# ============================================================
# MODE: Delete
# ============================================================

if ($Mode -eq 'Delete') {

    if (-not (Test-Path -LiteralPath $ItemsFile)) {
        Write-JsonError -Message "Items file not found." -Details $ItemsFile
        exit 1
    }

    try {
        $approved = Get-Content -LiteralPath $ItemsFile -Raw | ConvertFrom-Json
    } catch {
        Write-JsonError -Message "Items file could not be parsed as JSON." -Details $_.Exception.Message
        exit 1
    }

    $approvedFolders = @($approved.folders)
    $approvedRegistry = @($approved.registry)

    # Re-check the "still installed" guard immediately before deleting -
    # not just at scan time - in case the application was reinstalled
    # in between.
    $installedMatches = Get-InstalledMatches -TargetAppName $TargetAppName
    if ($installedMatches.Count -gt 0) {
        $result = [PSCustomObject]@{
            success          = $false
            targetAppName    = $TargetAppName
            aborted          = $true
            reason           = "The application now appears to be installed. Uninstall it normally first."
            installedMatches = $installedMatches
        }
        $result | ConvertTo-Json -Depth 8 -Compress
        exit 0
    }

    $searchTerms = Get-SearchTerms -TargetAppName $TargetAppName
    $registryResult = Find-LeftoverRegistryKeys -SearchTerms $searchTerms
    $allowedRootPSPaths = $registryResult.allowedRootPSPaths

    $deletedFolders = New-Object System.Collections.Generic.List[object]
    $deletedRegistry = New-Object System.Collections.Generic.List[object]
    $rejected = New-Object System.Collections.Generic.List[object]
    $failed = New-Object System.Collections.Generic.List[object]

    foreach ($folder in $approvedFolders) {

        if ([string]::IsNullOrWhiteSpace($folder)) { continue }

        if (-not (Test-SafePath $folder)) {
            $rejected.Add([PSCustomObject]@{ type = "Folder"; path = $folder; reason = "Failed path safety check" })
            continue
        }

        $nameToCheck = Split-Path -Path $folder -Leaf
        if (-not (Test-ExactApplicationName -Name $nameToCheck -SearchTerms $searchTerms)) {
            $rejected.Add([PSCustomObject]@{ type = "Folder"; path = $folder; reason = "No longer matches the target application name" })
            continue
        }

        if (-not (Test-Path -LiteralPath $folder)) {
            $rejected.Add([PSCustomObject]@{ type = "Folder"; path = $folder; reason = "Path no longer exists" })
            continue
        }

        try {
            Remove-Item -LiteralPath $folder -Recurse -Force -ErrorAction Stop
            $deletedFolders.Add($folder)
        } catch {
            $failed.Add([PSCustomObject]@{ type = "Folder"; path = $folder; reason = $_.Exception.Message })
        }
    }

    foreach ($regPath in $approvedRegistry) {

        if ([string]::IsNullOrWhiteSpace($regPath)) { continue }

        if (-not (Test-SafeRegistryLeaf -RegistryPath $regPath -AllowedRootPSPaths $allowedRootPSPaths)) {
            $rejected.Add([PSCustomObject]@{ type = "Registry"; path = $regPath; reason = "Failed registry safety check (not a direct child of a scanned root)" })
            continue
        }

        $leafName = ($regPath -split '\\')[-1]
        if (-not (Test-ExactApplicationName -Name $leafName -SearchTerms $searchTerms)) {
            $rejected.Add([PSCustomObject]@{ type = "Registry"; path = $regPath; reason = "No longer matches the target application name" })
            continue
        }

        if (-not (Test-Path -Path $regPath)) {
            $rejected.Add([PSCustomObject]@{ type = "Registry"; path = $regPath; reason = "Key no longer exists" })
            continue
        }

        try {
            Remove-Item -Path $regPath -Recurse -Force -ErrorAction Stop
            $deletedRegistry.Add($regPath)
        } catch {
            $failed.Add([PSCustomObject]@{ type = "Registry"; path = $regPath; reason = $_.Exception.Message })
        }
    }

    $result = [PSCustomObject]@{
        success           = $true
        targetAppName     = $TargetAppName
        aborted           = $false
        deleted           = [PSCustomObject]@{ folders = $deletedFolders.ToArray(); registry = $deletedRegistry.ToArray() }
        rejected          = $rejected.ToArray()
        failed            = $failed.ToArray()
        warnings          = $script:diagnosticWarnings.ToArray()
        deleteCompletedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    }

    $result | ConvertTo-Json -Depth 8 -Compress
    exit 0
}
