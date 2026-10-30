param(
    [Parameter(Mandatory)][string]$ManifestPath,
    [Parameter(Mandatory)][string]$OutputDir
)
$ErrorActionPreference = 'Stop'
$manifest = (Resolve-Path -LiteralPath $ManifestPath -ErrorAction Stop).Path
if ([IO.Path]::GetExtension($manifest) -ne '.psd1') { throw 'A .psd1 module manifest is required.' }
$name = [IO.Path]::GetFileNameWithoutExtension($manifest)
$metadata = Import-PowerShellDataFile -LiteralPath $manifest
if (-not $metadata.RootModule -or -not $metadata.ModuleVersion) {
    throw 'Manifest requires RootModule and ModuleVersion.'
}
$moduleInfo = Test-ModuleManifest -Path $manifest -ErrorAction Stop
$version = [string]$moduleInfo.Version
if (-not $version -or $moduleInfo.Name -ne $name) {
    throw "Module name/version mismatch: $name / $version."
}

$sourceDirectory = Split-Path -Parent $manifest
$root = Join-Path (Get-Location) 'out/module-stage'
$staged = Join-Path $root "$name/$version"
if (Test-Path -LiteralPath $root) { Remove-Item -LiteralPath $root -Recurse -Force }
New-Item -ItemType Directory -Path $staged -Force | Out-Null
Get-ChildItem -LiteralPath $sourceDirectory -Force |
    Copy-Item -Destination $staged -Recurse -Force

$stagedManifest = Join-Path $staged "$name.psd1"
if (-not (Test-Path -LiteralPath $stagedManifest -PathType Leaf)) {
    throw "Missing staged module manifest: $stagedManifest"
}
$null = Test-ModuleManifest -Path $stagedManifest -ErrorAction Stop
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
$archive = Join-Path (Resolve-Path -LiteralPath $OutputDir).Path "$name-$version.zip"
if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive -Force }
Compress-Archive -LiteralPath (Join-Path $root $name) -DestinationPath $archive

# Test the archive, not the staged source tree.
$extractRoot = Join-Path (Get-Location) 'out/module-extracted'
if (Test-Path -LiteralPath $extractRoot) { Remove-Item -LiteralPath $extractRoot -Recurse -Force }
Expand-Archive -LiteralPath $archive -DestinationPath $extractRoot
$env:PSModulePath = "$extractRoot$([IO.Path]::PathSeparator)$env:PSModulePath"
& pwsh -NoProfile -NonInteractive -File (Join-Path $PSScriptRoot 'verify.ps1') -ModuleName $name -Version $version -ExtractRoot $extractRoot
if ($LASTEXITCODE -ne 0) { throw 'Isolated ZIP module import/export verification failed.' }

if ($env:GITHUB_OUTPUT) {
    "module-zip=$archive" | Out-File $env:GITHUB_OUTPUT -Encoding utf8 -Append
    "module-name=$name" | Out-File $env:GITHUB_OUTPUT -Encoding utf8 -Append
    "module-version=$version" | Out-File $env:GITHUB_OUTPUT -Encoding utf8 -Append
}
Write-Host "Module package validated: $archive"
