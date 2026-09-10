param(
    [string]$Solution = ""
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$bundledPython = "C:\Users\86152\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$pythonExe = if (Test-Path -LiteralPath $bundledPython) { $bundledPython } else { "python" }

& $pythonExe (Join-Path $PSScriptRoot "data_pipeline.py") --root $root

if ($Solution) {
    $solutionPath = (Resolve-Path -LiteralPath $Solution).Path
} else {
    $finalPath = Join-Path $root "solution_long.csv"
    if (Test-Path -LiteralPath $finalPath) {
        $solutionPath = $finalPath
    } else {
        $solutionPath = Join-Path $root "scenario_data\provisional_solution_long.csv"
    }
}

& $pythonExe (Join-Path $PSScriptRoot "export_results.py") --root $root --solution $solutionPath

$excel = $null
try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    foreach ($name in @("result1.xlsx", "result2.xlsx", "result3.xlsx", "result4-2.xlsx", "result4-3.xlsx")) {
        $path = Join-Path $root $name
        $book = $excel.Workbooks.Open($path, 0, $false)
        $excel.CalculateFullRebuild()
        $book.Save()
        $book.Close($false)
    }
} finally {
    if ($excel) { $excel.Quit() }
}

& $pythonExe (Join-Path $PSScriptRoot "validate_results.py") --root $root --solution $solutionPath
& $pythonExe (Join-Path $PSScriptRoot "write_handoff.py") --root $root --solution $solutionPath
Write-Output "DONE: $root"
