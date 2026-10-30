$ErrorActionPreference = 'Stop'
$testFiles = if (Test-Path -LiteralPath $env:TEST_PATH) {
    @(Get-ChildItem -LiteralPath $env:TEST_PATH -Recurse -File -Filter '*.Tests.ps1')
} else { @() }
if (-not $testFiles.Count) {
    if ([bool]::Parse($env:REQUIRE_TESTS)) {
        throw "Pester tests are required but none were found in $($env:TEST_PATH)."
    }
    Write-Output 'No Pester tests; optional test stage skipped.'
    return
}

Install-PSResource -Name Pester -Version '6.2.0' -Scope CurrentUser -TrustRepository
Import-Module Pester -RequiredVersion '6.2.0' -ErrorAction Stop
$results = Join-Path (Get-Location) $env:RESULTS_PATH
New-Item -ItemType Directory -Path (Split-Path $results -Parent) -Force | Out-Null
$config = New-PesterConfiguration
$config.Run.Path = $env:TEST_PATH
$config.Run.PassThru = $true
$config.Output.Verbosity = 'Detailed'
$config.TestResult.Enabled = $true
$config.TestResult.OutputFormat = 'JUnitXml'
$config.TestResult.OutputPath = $results
$result = Invoke-Pester -Configuration $config
if ($result.Result -ne 'Passed') {
    throw "Pester failed: $($result.FailedCount) failing test(s), result $($result.Result)."
}
