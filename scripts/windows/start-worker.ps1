param([string]$ServiceName = "ATOS Worker")

$ErrorActionPreference = "Stop"
Start-Service -Name $ServiceName
Get-Service -Name $ServiceName
