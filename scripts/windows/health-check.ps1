param(
    [string]$ServerUrl = $env:ATOS_SERVER_URL,
    [string]$WorkerToken = $env:WORKER_API_TOKEN
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ServerUrl)) {
    throw "ATOS_SERVER_URL is required."
}
if ([string]::IsNullOrWhiteSpace($WorkerToken)) {
    throw "WORKER_API_TOKEN is required."
}

Invoke-RestMethod `
    -Method Get `
    -Uri "$ServerUrl/worker/health" `
    -Headers @{ "X-Worker-Token" = $WorkerToken }
