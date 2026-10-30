<#
.SYNOPSIS
Extracts public PowerShell module commands and authored Get-Help to reference JSON.
.DESCRIPTION
Imports the module and serializes Get-Help plus CommandInfo. The site build
runs separately, consuming only the emitted JSON. Module import executes
module initialization code, so only test repositories you trust.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$ManifestPath,
    [Parameter(Mandatory)][string]$OutputPath
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Get-Text {
    param($Value)
    if ($null -eq $Value) { return '' }
    if ($Value -is [string]) { return $Value.Trim() }
    if ($Value -is [System.Collections.IEnumerable]) {
        return (@($Value | ForEach-Object { Get-Text $_ }) -join "`n").Trim()
    }
    $p = $Value.PSObject.Properties['Text']
    if ($null -ne $p) { return Get-Text $p.Value }
    return ([string]$Value).Trim()
}

function Get-ParameterDescription {
    param($Help, [string]$Name)
    $parameters = @($Help.parameters.parameter | Where-Object { $null -ne $_ })
    $matching = @($parameters | Where-Object { [string]$_.name -eq $Name })
    if ($matching.Count -eq 0) { return '' }
    return Get-Text $matching[0].description
}

$manifest = (Resolve-Path -LiteralPath $ManifestPath).Path
$module = Import-Module -Name $manifest -PassThru -Force -ErrorAction Stop |
    Where-Object { $_ -is [System.Management.Automation.PSModuleInfo] } |
    Select-Object -First 1
if ($null -eq $module) { throw "Import-Module did not load: $manifest" }

$common = @(
    'Verbose', 'Debug', 'ErrorAction', 'WarningAction', 'InformationAction',
    'ErrorVariable', 'WarningVariable', 'InformationVariable', 'OutVariable',
    'OutBuffer', 'PipelineVariable', 'ProgressAction', 'WhatIf', 'Confirm'
)
$commands = @()
foreach ($command in @($module.ExportedCommands.Values | Sort-Object Name)) {
    if ($command.CommandType -notin @('Function', 'Cmdlet', 'Filter')) { continue }
    $help = Get-Help -Name $command.Name -Full -ErrorAction Stop
    $parameters = @()
    foreach ($parameter in @($command.Parameters.Values | Sort-Object Name)) {
        if ($parameter.Name -in $common) { continue }
        $mandatory = @(
            $command.ParameterSets |
                ForEach-Object { $_.Parameters } |
                Where-Object { $_.Name -eq $parameter.Name -and $_.IsMandatory }
        ).Count -gt 0
        $parameters += @{
            name = [string]$parameter.Name
            type = [string]$parameter.ParameterType.Name
            required = [bool]$mandatory
            description = [string](Get-ParameterDescription -Help $help -Name $parameter.Name)
        }
    }
    $examples = @()
    foreach ($example in @($help.examples.example | Where-Object { $null -ne $_ })) {
        $code = Get-Text $example.code
        if ([string]::IsNullOrWhiteSpace($code)) { continue }
        $examples += @{
            title = [string](Get-Text $example.title)
            code = [string]$code
            description = [string](Get-Text $example.remarks)
        }
    }
    $syntax = Get-Command -Name $command.Name -Module $module.Name -Syntax -ErrorAction Stop |
        Out-String
    $commands += @{
        name = [string]$command.Name
        kind = [string]$command.CommandType
        synopsis = [string](Get-Text $help.synopsis)
        description = [string](Get-Text $help.description)
        syntax = [string]$syntax.Trim()
        parameters = @($parameters)
        examples = @($examples)
    }
}
if ($commands.Count -eq 0) { throw "No exported functions/cmdlets found in $($module.Name)" }

$reference = @{
    schema_version = 1
    module = @{
        name = [string]$module.Name
        version = [string]$module.Version
        description = [string]$module.Description
    }
    commands = @($commands)
}
$destination = [IO.Path]::GetFullPath($OutputPath)
$folder = [IO.Path]::GetDirectoryName($destination)
[IO.Directory]::CreateDirectory($folder) | Out-Null
$reference | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $destination -Encoding utf8
Write-Output "Extracted $($commands.Count) commands from $($module.Name) $($module.Version)"
