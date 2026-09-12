<#
.SYNOPSIS
    Smart Old Applications & Leftovers Inventory - GUI Version

.DESCRIPTION
    READ-ONLY Windows application inventory.

    This script DOES NOT:
    - Delete files
    - Delete folders
    - Delete Registry keys
    - Uninstall applications
    - Modify system settings

    It scans:
    1. Registered applications
    2. Broken application registrations
    3. Possible orphaned Registry entries
    4. Possible old application folders

    Designed to be called by a Desktop GUI application.

.EXAMPLE
    powershell.exe -NoProfile -ExecutionPolicy Bypass `
        -File ".\Old-Applications-Inventory.ps1" `
        -OutputJson

.EXAMPLE
    powershell.exe -NoProfile -ExecutionPolicy Bypass `
        -File ".\Old-Applications-Inventory.ps1" `
        -OutputJson -OutputFile "result.json"
#>

param(
    [switch]$OutputJson,

    [string]$OutputFile
)

$ErrorActionPreference = "SilentlyContinue"


# ============================================================
# HELPER FUNCTIONS
# ============================================================

function Normalize-Name {
    param(
        [string]$Text
    )

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return ""
    }

    return ($Text.ToLower() -replace '[^a-z0-9]', '')
}


function Test-IsGenericFolder {
    param(
        [string]$FolderName
    )

    $genericFolders = @(
        "Microsoft",
        "Google",
        "Android",
        "Windows",
        "WindowsApps",
        "Common Files",
        "CommonFiles",
        "System",
        "System32",
        "SysWOW64",
        "Internet Explorer",
        "Packages",
        "Programs",
        "Program Files",
        "ProgramData",
        "Desktop",
        "Templates",
        "Public",
        "Default",
        "OneDrive",
        "Mozilla",
        "Intel",
        "NVIDIA",
        "AMD",
        "Drivers",
        "Windows Defender",
        "Microsoft.NET",
        "Fonts",
        "Logs",
        "Temp",
        "Cache",
        "Caches"
    )

    $normalizedFolder = Normalize-Name $FolderName

    foreach ($generic in $genericFolders) {

        if ($normalizedFolder -eq (Normalize-Name $generic)) {
            return $true
        }
    }

    return $false
}


function Test-IsKnownSystemComponent {
    param(
        [string]$Name,
        [string]$Publisher
    )

    $systemKeywords = @(
        "Microsoft Visual C++",
        "Microsoft .NET",
        "Microsoft Windows",
        "Windows SDK",
        "Windows Desktop Runtime",
        "ASP.NET Core",
        "Microsoft Update",
        "Microsoft Edge WebView",
        "WebView2",
        "Microsoft Office",
        "Office 16",
        "Update for Windows",
        "Runtime",
        "Targeting Pack",
        "Redistributable",
        "Toolset",
        "Manifest",
        "Workload",
        "Mono Toolchain",
        "Emscripten"
    )

    foreach ($keyword in $systemKeywords) {

        if (
            $Name -like "*$keyword*" -or
            $Publisher -like "*$keyword*"
        ) {
            return $true
        }
    }

    return $false
}


function Get-CommandPath {
    param(
        [string]$Command
    )

    if ([string]::IsNullOrWhiteSpace($Command)) {
        return $null
    }

    $expanded = [Environment]::ExpandEnvironmentVariables(
        $Command.Trim()
    )

    if ($expanded -match '^"([^"]+)"') {
        return $Matches[1]
    }

    if ($expanded -match '^([^\s]+\.exe)') {
        return $Matches[1]
    }

    return $null
}


function Test-CommandExecutable {
    param(
        [string]$Command
    )

    $path = Get-CommandPath $Command

    if (-not $path) {
        return $false
    }

    return Test-Path -LiteralPath $path
}


# ============================================================
# DATA
# ============================================================

$applications = New-Object System.Collections.Generic.List[object]


# ============================================================
# REGISTRY LOCATIONS
# ============================================================

$registryPaths = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*"
)


# ============================================================
# STEP 1
# READ ALL REGISTERED APPLICATIONS
# ============================================================

foreach ($path in $registryPaths) {

    $records = Get-ItemProperty `
        $path `
        -ErrorAction SilentlyContinue

    foreach ($record in $records) {

        if ([string]::IsNullOrWhiteSpace($record.DisplayName)) {
            continue
        }

        $displayName = [string]$record.DisplayName
        $publisher = [string]$record.Publisher
        $installLocation = [string]$record.InstallLocation
        $uninstallString = [string]$record.UninstallString
        $quietUninstallString = [string]$record.QuietUninstallString
        $displayIcon = [string]$record.DisplayIcon


        # ----------------------------------------------------
        # Install Date
        # ----------------------------------------------------

        $installDate = $null

        if ($record.InstallDate) {

            try {

                $installDate = [datetime]::ParseExact(
                    [string]$record.InstallDate,
                    "yyyyMMdd",
                    $null
                ).ToString("yyyy-MM-dd")

            }
            catch {

                $installDate = [string]$record.InstallDate
            }
        }


        # ----------------------------------------------------
        # System / Runtime classification
        # ----------------------------------------------------

        $isSystemComponent = Test-IsKnownSystemComponent `
            -Name $displayName `
            -Publisher $publisher


        # ----------------------------------------------------
        # Install Location
        # ----------------------------------------------------

        $installLocationExists = $false

        if (-not [string]::IsNullOrWhiteSpace($installLocation)) {

            $installLocationExists = Test-Path `
                -LiteralPath $installLocation
        }


        # ----------------------------------------------------
        # Uninstaller
        # ----------------------------------------------------

        $uninstallerExists = $false

        $uninstallerPath = Get-CommandPath `
            $uninstallString

        if ($uninstallerPath) {

            $uninstallerExists = Test-Path `
                -LiteralPath $uninstallerPath
        }


        # ----------------------------------------------------
        # Display Icon
        # ----------------------------------------------------

        $iconExists = $false

        $iconPath = Get-CommandPath `
            $displayIcon

        if ($iconPath) {

            $iconExists = Test-Path `
                -LiteralPath $iconPath
        }


        # ----------------------------------------------------
        # Status
        # ----------------------------------------------------

        $status = "Registered"

        if ($installLocationExists) {

            $status = "Installed"

        }
        elseif ($uninstallerExists) {

            $status = "Registered - Uninstaller Found"

        }
        elseif ($iconExists) {

            $status = "Registered - Application Evidence Found"

        }
        elseif (
            -not [string]::IsNullOrWhiteSpace(
                $installLocation
            )
        ) {

            $status = "Possible Broken Registration"

        }
        else {

            $status = "Registered - Location Not Specified"
        }


        # ----------------------------------------------------
        # Add application
        # ----------------------------------------------------

        $applications.Add(
            [PSCustomObject]@{

                Name = $displayName

                Publisher = $publisher

                InstallDate = $installDate

                InstallLocation = $installLocation

                InstallLocationExists = $installLocationExists

                UninstallString = $uninstallString

                QuietUninstallString = $quietUninstallString

                UninstallerExists = $uninstallerExists

                DisplayIcon = $displayIcon

                IconExists = $iconExists

                Status = $status

                Type = if ($isSystemComponent) {
                    "System/Runtime Component"
                }
                else {
                    "Application"
                }

                RegistryPath = [string]$record.PSPath
            }
        )
    }
}


# ============================================================
# REMOVE DUPLICATES
# ============================================================

$uniqueApplications = @(
    $applications |
        Sort-Object Name, Publisher, InstallLocation -Unique
)


# ============================================================
# STEP 2
# BROKEN REGISTRATIONS
# ============================================================

$brokenRegistrations = @(
    $uniqueApplications |
        Where-Object {

            $_.InstallLocation -and
            -not $_.InstallLocationExists
        }
)


# ============================================================
# STEP 3
# ORPHANED REGISTRY ENTRIES
# ============================================================

$orphanedRegistry = New-Object System.Collections.Generic.List[object]


foreach ($app in $uniqueApplications) {

    $reasons = New-Object System.Collections.Generic.List[string]


    # --------------------------------------------------------
    # Missing installation directory
    # --------------------------------------------------------

    if (
        $app.InstallLocation -and
        -not $app.InstallLocationExists
    ) {

        $reasons.Add(
            "Registered installation location does not exist"
        )
    }


    # --------------------------------------------------------
    # Missing uninstaller
    # --------------------------------------------------------

    if (
        $app.UninstallString -and
        -not $app.UninstallerExists
    ) {

        $commandPath = Get-CommandPath `
            $app.UninstallString

        if ($commandPath) {

            $reasons.Add(
                "Registered uninstaller executable does not exist"
            )
        }
    }


    # --------------------------------------------------------
    # Add orphan candidate
    # --------------------------------------------------------

    if ($reasons.Count -gt 0) {

        $orphanedRegistry.Add(
            [PSCustomObject]@{

                Application = $app.Name

                Publisher = $app.Publisher

                Installed = $app.InstallDate

                Confidence = "MEDIUM"

                Reason = (
                    $reasons -join "; "
                )

                Registry = $app.RegistryPath
            }
        )
    }
}


$orphanedRegistry = @(
    $orphanedRegistry |
        Sort-Object Registry -Unique
)


# ============================================================
# STEP 4
# POSSIBLE OLD APPLICATION FOLDERS
# ============================================================

$searchLocations = @(
    $env:LOCALAPPDATA,
    $env:APPDATA,
    $env:PROGRAMDATA,
    $env:ProgramFiles,
    ${env:ProgramFiles(x86)}
)


$possibleOldFolders =
    New-Object System.Collections.Generic.List[object]


# Only actual applications

$realApplications = @(
    $uniqueApplications |
        Where-Object {
            $_.Type -eq "Application"
        }
)


foreach ($location in $searchLocations) {

    if ([string]::IsNullOrWhiteSpace($location)) {
        continue
    }

    if (-not (Test-Path -LiteralPath $location)) {
        continue
    }


    try {

        $folders = Get-ChildItem `
            -Path $location `
            -Directory `
            -Force `
            -ErrorAction SilentlyContinue


        foreach ($folder in $folders) {

            if (Test-IsGenericFolder $folder.Name) {
                continue
            }


            $folderNormalized =
                Normalize-Name $folder.Name


            if ($folderNormalized.Length -lt 5) {
                continue
            }


            foreach ($app in $realApplications) {

                $appNormalized =
                    Normalize-Name $app.Name


                if ($appNormalized.Length -lt 5) {
                    continue
                }


                if ($folderNormalized -eq $appNormalized) {

                    # ------------------------------------------------
                    # Same as valid installation location
                    # ------------------------------------------------

                    if (
                        $app.InstallLocation -and
                        $app.InstallLocationExists
                    ) {

                        try {

                            $registeredPath =
                                [System.IO.Path]::GetFullPath(
                                    $app.InstallLocation
                                ).TrimEnd('\')

                            $folderPath =
                                $folder.FullName.TrimEnd('\')


                            if (
                                $registeredPath -ieq $folderPath
                            ) {

                                continue
                            }
                        }
                        catch {}
                    }


                    # ------------------------------------------------
                    # Confidence
                    # ------------------------------------------------

                    $confidence = "LOW"

                    $reason =
                        "Recognizable application folder found"


                    if (
                        -not $app.InstallLocation -or
                        -not $app.InstallLocationExists
                    ) {

                        $confidence = "MEDIUM"

                        $reason =
                            "Application folder found, but registered installation evidence is missing"
                    }


                    $possibleOldFolders.Add(
                        [PSCustomObject]@{

                            Application = $app.Name

                            Folder = $folder.Name

                            Path = $folder.FullName

                            Modified = $folder.LastWriteTime

                            Confidence = $confidence

                            Reason = $reason
                        }
                    )


                    break
                }
            }
        }
    }
    catch {}
}


# ============================================================
# REMOVE DUPLICATE FOLDERS
# ============================================================

$possibleOldFolders = @(
    $possibleOldFolders |
        Sort-Object Path, Application -Unique
)


# ============================================================
# SUMMARY
# ============================================================

$summary = [PSCustomObject]@{

    TotalApplications =
        $uniqueApplications.Count

    BrokenRegistrations =
        $brokenRegistrations.Count

    PossibleOrphanedRegistryEntries =
        $orphanedRegistry.Count

    PossibleOldApplicationFolders =
        $possibleOldFolders.Count

    ReadOnly = $true

    ScanCompletedAt =
        (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
}


# ============================================================
# FINAL RESULT
# ============================================================

$result = [PSCustomObject]@{

    success = $true

    readOnly = $true

    summary = $summary

    applications = $uniqueApplications

    brokenRegistrations = $brokenRegistrations

    orphanedRegistry = $orphanedRegistry

    possibleOldFolders = $possibleOldFolders
}


# ============================================================
# OUTPUT
# ============================================================

$json = $result |
    ConvertTo-Json `
        -Depth 10 `
        -Compress


# ------------------------------------------------------------
# If OutputFile was supplied
# ------------------------------------------------------------

if (-not [string]::IsNullOrWhiteSpace($OutputFile)) {

    try {

        $json |
            Set-Content `
                -LiteralPath $OutputFile `
                -Encoding UTF8
    }
    catch {

        $errorResult = [PSCustomObject]@{

            success = $false

            error = $_.Exception.Message
        }

        $errorResult |
            ConvertTo-Json `
                -Compress

        exit 1
    }
}


# ------------------------------------------------------------
# GUI mode
# ------------------------------------------------------------

if ($OutputJson) {

    Write-Output $json

}
else {

    # Human-readable mode
    # Useful when testing manually.

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "       SMART APPLICATION INVENTORY" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""

    Write-Host "READ-ONLY MODE" -ForegroundColor Green
    Write-Host ""

    Write-Host "Total applications: " -NoNewline
    Write-Host $summary.TotalApplications -ForegroundColor Yellow

    Write-Host "Broken registrations: " -NoNewline
    Write-Host $summary.BrokenRegistrations -ForegroundColor Yellow

    Write-Host "Possible orphan Registry entries: " -NoNewline
    Write-Host $summary.PossibleOrphanedRegistryEntries -ForegroundColor Yellow

    Write-Host "Possible old application folders: " -NoNewline
    Write-Host $summary.PossibleOldApplicationFolders -ForegroundColor Yellow

    Write-Host ""

    Write-Host "No files, folders, Registry keys or settings were modified." `
        -ForegroundColor Green

    Write-Host ""
}