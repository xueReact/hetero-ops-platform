param([switch]$Standalone, [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
# ASCII script keeps Windows PowerShell 5.1 from misreading UTF-8 messages.
$docker = Get-Command docker.exe -ErrorAction SilentlyContinue
if (-not $docker) {
    foreach ($candidate in @("$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe", "$env:ProgramFiles\Docker\Docker\resources\bin\docker.exe")) {
        if (Test-Path -LiteralPath $candidate) { $docker = Get-Item -LiteralPath $candidate; break }
    }
}
if (-not $docker) { throw 'Docker Desktop is required.' }
$dockerPath = if ($docker.Source) { $docker.Source } else { $docker.FullName }
& $dockerPath info --format '{{.ServerVersion}}'
if ($LASTEXITCODE -ne 0) { throw 'Start Docker Desktop and wait for the engine before retrying.' }
Push-Location $PSScriptRoot
$previousUpstream = $env:AIRPORT_UPSTREAM
$previousRuntime = $env:AIRPORT_RUNTIME_IMAGE
try {
    $reuse = $false
    if (-not $Standalone) {
        try {
            $status = Invoke-RestMethod 'http://127.0.0.1:8094/api/status' -TimeoutSec 4
            $reuse = ($null -ne $status.devices)
        } catch { }
    }
    if ($reuse) {
        Write-Host 'Connecting the existing airport service on port 8094.'
        $env:AIRPORT_UPSTREAM = 'http://host.docker.internal:8094'
        & $dockerPath compose up -d --build platform
    } else {
        Write-Host 'Starting the bundled airport service (first build may take time).'
        $env:AIRPORT_UPSTREAM = 'http://airport:8080'
        & $dockerPath image inspect rmf-airport-sim:humble *> $null
        if ($LASTEXITCODE -eq 0) { $env:AIRPORT_RUNTIME_IMAGE = 'rmf-airport-sim:humble' }
        & $dockerPath compose --profile airport up -d --build airport platform
    }
    if ($LASTEXITCODE -ne 0) { throw 'Container startup failed. Review the Docker output above.' }
    $port = if ($env:FIRE_PUBLIC_PORT) { $env:FIRE_PUBLIC_PORT } else { '8001' }
    $url = "http://localhost:$port"
    $ready = $false
    for ($attempt = 0; $attempt -lt 45; $attempt++) {
        try {
            $health = Invoke-RestMethod "$url/api/health" -TimeoutSec 3
            if ($health.ok) { $ready = $true; break }
        } catch { }
        Start-Sleep -Seconds 2
    }
    if (-not $ready) { throw "Platform did not become ready. Run: docker compose logs platform" }
    Write-Host "Platform: $url"
    Write-Host "Airport console: $url/airport-console"
    Write-Host 'The console shows its connection state while the airport is warming up.'
    if (-not $NoBrowser) { Start-Process "$url/airport-console" }
} finally {
    $env:AIRPORT_UPSTREAM = $previousUpstream
    $env:AIRPORT_RUNTIME_IMAGE = $previousRuntime
    Pop-Location
}
