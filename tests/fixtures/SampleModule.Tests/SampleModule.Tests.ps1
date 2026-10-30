BeforeAll {
    Import-Module (Join-Path $PSScriptRoot '../SampleModule/SampleModule.psd1') -Force
}

Describe 'SampleModule public API' {
    It 'loads the declared public command' {
        Get-Greeting -Name 'World' | Should -Be 'Hello, World!'
    }

    It 'exposes one public function' {
        @(Get-Command -Module SampleModule -CommandType Function).Count | Should -Be 1
    }
}
