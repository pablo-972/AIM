param(
    [switch]$Backend,
    [switch]$NoFrontend
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
$SetupDir = Join-Path $RootDir "setup"
$StateDir = Join-Path $RootDir ".aim-runtime"
$LogDir = Join-Path $RootDir "logs"
$SetupVenvDir = Join-Path $SetupDir ".venv-windows"
$SetupRequirements = Join-Path $SetupDir "requirements.txt"

$ApiPidFile = Join-Path $StateDir "vbox-api.pid"
$ApiHealthUrl = "http://127.0.0.1:8090/health"
$ApiStartupTimeoutSeconds = 20
$ApiStartupPollSeconds = 1

New-Item -ItemType Directory -Force -Path $StateDir | Out-Null
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Test-TrackedProcess {
    param([string]$PidFile)

    if (-not (Test-Path $PidFile)) {
        return $false
    }

    $TrackedPid = Get-Content $PidFile -ErrorAction SilentlyContinue
    if (-not $TrackedPid) {
        return $false
    }

    $Process = Get-Process -Id ([int]$TrackedPid) -ErrorAction SilentlyContinue
    return $null -ne $Process
}

function Get-SystemPythonCommand {
    $Python = Get-Command python -ErrorAction SilentlyContinue
    if ($Python) {
        return @{
            FilePath = $Python.Source
            Prefix = @()
        }
    }

    $Py = Get-Command py -ErrorAction SilentlyContinue
    if ($Py) {
        return @{
            FilePath = $Py.Source
            Prefix = @("-3")
        }
    }

    throw "Python is required but was not found."
}

function Invoke-PythonCommand {
    param(
        [hashtable]$Command,
        [string[]]$Arguments
    )

    $FullArguments = @($Command.Prefix) + $Arguments
    & $Command.FilePath @FullArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed: $($Command.FilePath) $($FullArguments -join ' ')"
    }
}

function Initialize-SetupPython {
    if (-not (Test-Path $SetupRequirements)) {
        throw "Missing setup requirements file: $SetupRequirements"
    }

    $VenvPython = Join-Path $SetupVenvDir "Scripts\python.exe"
    if (-not (Test-Path $VenvPython)) {
        Write-Host "Creating setup Python virtual environment..."
        $SystemPython = Get-SystemPythonCommand
        Invoke-PythonCommand -Command $SystemPython -Arguments @("-m", "venv", $SetupVenvDir)
    }

    & $VenvPython -m pip install -r $SetupRequirements | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "Could not install setup Python requirements."
    }

    return $VenvPython
}

function Get-PythonCommand {
    $VenvPython = Initialize-SetupPython
    return @{
        FilePath = $VenvPython
        Arguments = @("-B", "-m", "setup.api")
    }
}

function Test-VirtualBoxApiHealth {
    try {
        $Response = Invoke-RestMethod -Uri $ApiHealthUrl -TimeoutSec 2
        return $Response.status -eq "ok"
    } catch {
        return $false
    }
}

function Show-VirtualBoxApiLogs {
    $Stdout = Join-Path $LogDir "vbox-api.log"
    $Stderr = Join-Path $LogDir "vbox-api.err.log"

    if (Test-Path $Stdout) {
        Write-Host "VirtualBox Manager API stdout:"
        Get-Content $Stdout -Tail 40 | Out-Host
    }

    if (Test-Path $Stderr) {
        Write-Host "VirtualBox Manager API stderr:"
        Get-Content $Stderr -Tail 80 | Out-Host
    }
}

function Wait-VirtualBoxApiHealth {
    param([System.Diagnostics.Process]$Process)

    $Deadline = (Get-Date).AddSeconds($ApiStartupTimeoutSeconds)
    while ((Get-Date) -lt $Deadline) {
        if (Test-VirtualBoxApiHealth) {
            return $true
        }

        if ($Process.HasExited) {
            return $false
        }

        Start-Sleep -Seconds $ApiStartupPollSeconds
    }

    return $false
}

function Start-VirtualBoxApi {
    if (Test-TrackedProcess -PidFile $ApiPidFile) {
        $TrackedPid = Get-Content $ApiPidFile
        if (Test-VirtualBoxApiHealth) {
            Write-Host "VirtualBox Manager API already running (pid $TrackedPid)."
            return
        }

        throw "VirtualBox Manager API pid $TrackedPid is running, but $ApiHealthUrl did not respond with status ok."
    }

    if (Test-VirtualBoxApiHealth) {
        Write-Host "VirtualBox Manager API already reachable at $ApiHealthUrl."
        return
    }

    $Command = Get-PythonCommand
    $Stdout = Join-Path $LogDir "vbox-api.log"
    $Stderr = Join-Path $LogDir "vbox-api.err.log"

    Write-Host "Starting VirtualBox Manager API..."
    $Process = Start-Process `
        -FilePath $Command.FilePath `
        -ArgumentList $Command.Arguments `
        -WorkingDirectory $RootDir `
        -RedirectStandardOutput $Stdout `
        -RedirectStandardError $Stderr `
        -WindowStyle Hidden `
        -PassThru

    Set-Content -Path $ApiPidFile -Value $Process.Id
    if (Wait-VirtualBoxApiHealth -Process $Process) {
        Write-Host "VirtualBox Manager API started (pid $($Process.Id))."
        return
    }

    Show-VirtualBoxApiLogs
    throw "VirtualBox Manager API did not become healthy at $ApiHealthUrl."
}

function Start-DockerCompose {
    $Docker = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $Docker) {
        throw "Docker is required but was not found."
    }

    Write-Host "Starting Docker Compose services..."
    Push-Location $RootDir
    try {
        if ($Backend -and -not $NoFrontend) {
            & docker compose --profile backend --profile frontend up -d --build
        } elseif ($Backend) {
            & docker compose --profile backend up -d --build
        } else {
            & docker compose --profile cli up -d --build
        }
    } finally {
        Pop-Location
    }
}

Start-VirtualBoxApi
Start-DockerCompose

Write-Host "AIM startup completed."
