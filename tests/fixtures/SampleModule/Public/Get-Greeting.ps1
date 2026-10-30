function Get-Greeting {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Name)

    "Hello, $Name!"
}
