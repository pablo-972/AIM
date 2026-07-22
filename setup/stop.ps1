param()

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
$StateDir = Join-Path $RootDir ".aim-runtime"

$ApiPidFile = Join-Path $StateDir "vbox-api.pid"

function Stop-TrackedProcess {
    param(
        [string]$Name,
        [string]$PidFile
    )

    if (-not (Test-Path $PidFile)) {
        Write-Host "$Name is not tracked."
        return
    }

    $TrackedPid = Get-Content $PidFile -ErrorAction SilentlyContinue
    if (-not $TrackedPid) {
        Remove-Item -Path $PidFile -Force -ErrorAction SilentlyContinue
        Write-Host "$Name pid file was empty."
        return
    }

    $Process = Get-Process -Id ([int]$TrackedPid) -ErrorAction SilentlyContinue
    if ($Process) {
        Write-Host "Stopping $Name (pid $TrackedPid)..."
        Stop-Process -Id ([int]$TrackedPid) -Force -ErrorAction SilentlyContinue
    } else {
        Write-Host "$Name was not running."
    }

    Remove-Item -Path $PidFile -Force -ErrorAction SilentlyContinue
}

function Stop-DockerCompose {
    $Docker = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $Docker) {
        Write-Host "Docker not found. Skipping Docker Compose shutdown."
        return
    }

    Write-Host "Stopping Docker Compose services..."
    Push-Location $RootDir
    try {
        & docker compose --profile backend --profile frontend down
    } finally {
        Pop-Location
    }
}

Stop-DockerCompose
Stop-TrackedProcess -Name "VirtualBox Manager API" -PidFile $ApiPidFile

Write-Host "AIM shutdown completed."
