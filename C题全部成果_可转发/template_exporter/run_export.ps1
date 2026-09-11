param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $PSScriptRoot
$solution = Join-Path $packageRoot "solution_long.csv"
$workbookRoot = Join-Path $packageRoot "official_results"

& $PythonExe (Join-Path $PSScriptRoot "export_official_templates.py") --root $packageRoot --output-dir $workbookRoot --solution $solution
Write-Output "Official workbooks exported: $workbookRoot"
Write-Output "Next: open all five files in desktop Microsoft Excel, run Calculate Now/Calculate Sheet, save, then run validate_official_results.py."
