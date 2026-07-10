param([string]$ServiceName = "ATOS Worker")

$ErrorActionPreference = "Stop"
Stop-Service -Name $ServiceName
Get-Service -Name $ServiceName
