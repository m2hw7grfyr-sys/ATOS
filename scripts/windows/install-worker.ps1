param(
    [string]$ServiceName = "ATOS Worker",
    [string]$WorkerRoot = "C:\ATOS\worker",
    [string]$ServerUrl = $env:ATOS_SERVER_URL,
    [string]$WorkerToken = $env:WORKER_API_TOKEN,
    [string]$WorkerName = $env:COMPUTERNAME,
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ServerUrl)) {
    throw "ATOS_SERVER_URL is required. Example: https://atos.example.com"
}
if ([string]::IsNullOrWhiteSpace($WorkerToken)) {
    throw "WORKER_API_TOKEN is required."
}

New-Item -ItemType Directory -Force -Path $WorkerRoot | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $WorkerRoot "logs") | Out-Null

$runnerPath = Join-Path $WorkerRoot "atos-worker-runner.ps1"
$runner = @"
`$env:ATOS_SERVER_URL = "$ServerUrl"
`$env:WORKER_API_TOKEN = "$WorkerToken"
`$env:ATOS_WORKER_NAME = "$WorkerName"
`$env:ATOS_WORKER_LOG_DIR = "$(Join-Path $WorkerRoot "logs")"
Set-Location "$WorkerRoot"
while (`$true) {
    try {
        `$body = @{
            name = `$env:ATOS_WORKER_NAME
            hostname = `$env:COMPUTERNAME
            os = "Windows"
            version = "sprint-06"
            runtime_status = "READY"
            capabilities = @{ AI = `$true; Browser = `$true; TGE = `$true; Playwright = `$true; Embedding = `$true }
        } | ConvertTo-Json -Depth 5
        Invoke-RestMethod -Method Post -Uri "`$env:ATOS_SERVER_URL/workers/register" -Headers @{ "X-Worker-Token" = `$env:WORKER_API_TOKEN } -Body `$body -ContentType "application/json" | Out-Null
        break
    } catch {
        Start-Sleep -Seconds 15
    }
}
while (`$true) {
    try {
        `$cpu = (Get-Counter '\Processor(_Total)\% Processor Time').CounterSamples.CookedValue
        `$os = Get-CimInstance Win32_OperatingSystem
        `$memoryUsed = [math]::Round(((`$os.TotalVisibleMemorySize - `$os.FreePhysicalMemory) / `$os.TotalVisibleMemorySize) * 100, 2)
        `$payload = @{
            worker_id = `$env:ATOS_WORKER_NAME
            timestamp = (Get-Date).ToUniversalTime().ToString("o")
            cpu = [math]::Round(`$cpu, 2)
            memory = `$memoryUsed
            gpu = `$null
            runtime_status = "READY"
            capabilities = @{ AI = `$true; Browser = `$true; TGE = `$true; Playwright = `$true; Embedding = `$true }
        } | ConvertTo-Json -Depth 5
        Invoke-RestMethod -Method Post -Uri "`$env:ATOS_SERVER_URL/workers/heartbeat" -Headers @{ "X-Worker-Token" = `$env:WORKER_API_TOKEN } -Body `$payload -ContentType "application/json" | Out-Null
        Start-Sleep -Seconds 30
    } catch {
        Add-Content -Path (Join-Path `$env:ATOS_WORKER_LOG_DIR "worker-error.log") -Value "`${(Get-Date).ToString('o')} `$($_.Exception.Message)"
        Start-Sleep -Seconds 5
        Start-Sleep -Seconds 10
        Start-Sleep -Seconds 15
        Start-Sleep -Seconds 30
    }
}
"@
Set-Content -Path $runnerPath -Value $runner -Encoding UTF8

$binPath = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$runnerPath`""
$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    sc.exe config "$ServiceName" binPath= "$binPath" start= auto | Out-Null
} else {
    New-Service -Name $ServiceName -BinaryPathName $binPath -DisplayName $ServiceName -StartupType Automatic | Out-Null
}

Start-Service -Name $ServiceName
Write-Host "$ServiceName installed and started."
