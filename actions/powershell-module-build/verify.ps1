param(
    [Parameter(Mandatory)][string]$ModuleName,
    [Parameter(Mandatory)][string]$Version,
    [Parameter(Mandatory)][string]$ExtractRoot
)
$ErrorActionPreference = 'Stop'
$moduleDir = Join-Path $ExtractRoot "$ModuleName/$Version"
$manifest = Join-Path $moduleDir "$ModuleName.psd1"
if (-not (Test-Path -LiteralPath $manifest -PathType Leaf)) {
    throw "Missing manifest after archive extraction: $manifest"
}
$null = Test-ModuleManifest -Path $manifest -ErrorAction Stop
$metadata = Import-PowerShellDataFile -LiteralPath $manifest
$expected = @($metadata.FunctionsToExport)
if ($expected.Count -eq 0 -or $expected -contains '*') {
    throw 'Explicit FunctionsToExport is required; wildcard exports are not accepted.'
}

$loaded = Import-Module -Name $ModuleName -RequiredVersion ([version]$Version) -Force -PassThru -ErrorAction Stop
$actualBase = [IO.Path]::GetFullPath($loaded.ModuleBase)
$expectedBase = [IO.Path]::GetFullPath($moduleDir)
if ($actualBase -ne $expectedBase) {
    throw "Unexpected module loaded from $actualBase instead of $expectedBase"
}
$actual = @(Get-Command -Module $ModuleName -CommandType Function | Select-Object -ExpandProperty Name)
$missing = @($expected | Where-Object { $actual -notcontains $_ })
$extra = @($actual | Where-Object { $expected -notcontains $_ })
if ($missing.Count -or $extra.Count) {
    throw "Export mismatch: missing [$($missing -join ', ')], extra [$($extra -join ', ')]."
}
Write-Output "Isolated Import-Module verified: $ModuleName $Version, exports [$($actual -join ', ')]"
