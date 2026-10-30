# Runs in the caller's repository; source tree is never modified.
$ErrorActionPreference = 'Stop'
$current = $PSVersionTable.PSVersion
if ($current -lt [version]$env:MIN_PS_VERSION) {
    throw "PowerShell $($env:MIN_PS_VERSION) or newer required; found $current."
}
Write-Output "PowerShell $current (minimum 7.6.9 by default)"

$files = @(Get-ChildItem -LiteralPath . -Recurse -File |
    Where-Object Extension -In '.ps1', '.psm1', '.psd1')
foreach ($file in $files) {
    $tokens = $null
    $errors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile(
        $file.FullName, [ref]$tokens, [ref]$errors
    )
    foreach ($issue in $errors) {
        Write-Output "::error file=$($file.FullName),line=$($issue.Extent.StartLineNumber)::$($issue.Message)"
    }
    if ($errors.Count) { throw "PowerShell syntax error: $($file.FullName)" }
}

Install-PSResource -Name PSScriptAnalyzer -Scope CurrentUser -TrustRepository
Import-Module PSScriptAnalyzer -ErrorAction Stop
$issues = @(foreach ($file in $files) {
    Invoke-ScriptAnalyzer -Path $file.FullName -Severity Error,Warning
})
foreach ($issue in $issues) {
    Write-Output "::error file=$($issue.ScriptName),line=$($issue.Line)::$($issue.Message)"
}
if ($issues.Count) { throw "$($issues.Count) PSScriptAnalyzer issues found." }
