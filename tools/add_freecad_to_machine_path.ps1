$ErrorActionPreference = 'Stop'

$freecadRoot = 'D:\Program Files (x86)\FreeCAD_weekly-2025.12.31-Windows-x86_64-py311'
$pathsToAdd = @(
    $freecadRoot,
    (Join-Path $freecadRoot 'bin')
)

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
$adminRole = [Security.Principal.WindowsBuiltInRole]::Administrator

if (-not $principal.IsInRole($adminRole)) {
    throw 'Please run this script as Administrator to update the machine PATH for all users.'
}

foreach ($item in $pathsToAdd) {
    if (-not (Test-Path -LiteralPath $item)) {
        throw "Path does not exist: $item"
    }
}

$machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
$parts = @()
if ($machinePath) {
    $parts = $machinePath -split ";" | Where-Object { $_ -ne "" }
}

$changed = $false
foreach ($item in $pathsToAdd) {
    $normalizedItem = $item.TrimEnd([char]92)
    $exists = $false
    foreach ($part in $parts) {
        if ($part.TrimEnd([char]92) -ieq $normalizedItem) {
            $exists = $true
            break
        }
    }

    if (-not $exists) {
        $parts += $item
        $changed = $true
        Write-Host "ADD $item"
    } else {
        Write-Host "SKIP existing $item"
    }
}

if ($changed) {
    [Environment]::SetEnvironmentVariable("Path", ($parts -join ";"), "Machine")
    Write-Host "Machine PATH updated. Open a new terminal before testing FreeCAD commands."
} else {
    Write-Host "Machine PATH already contains FreeCAD paths."
}

Write-Host ""
Write-Host "Test commands:"
Write-Host "  FreeCADCmd.exe --version"
Write-Host "  freecadcmd.exe --version"
Write-Host "  python.exe -c `"import FreeCAD; print(FreeCAD.Version())`""
