param(
    [Parameter(Mandatory=$true)][string]$DataRoot,
    [string]$PythonExe = "python",
    [int]$ScenarioCount = 8
)

$ErrorActionPreference = "Stop"
$out = $PSScriptRoot
& $PythonExe (Join-Path $out "simulation_source\run_pipeline.py") --data-root $DataRoot --output-root $out --scenario-count $ScenarioCount
& $PythonExe (Join-Path $out "simulation_source\run_settlement_sensitivity.py") --data-root $DataRoot --output-root $out
Write-Output "Numerical results regenerated in $out"

