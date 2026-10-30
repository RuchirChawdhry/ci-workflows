function Get-Greeting {
    <#
    .SYNOPSIS
    Creates a friendly greeting.

    .DESCRIPTION
    Formats a greeting for the supplied person's name.

    .PARAMETER Name
    Name of the person to greet.

    .EXAMPLE
    Get-Greeting -Name 'World'

    Returns the greeting 'Hello, World!'.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Name)

    "Hello, $Name!"
}
