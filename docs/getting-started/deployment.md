# Deployment

AIM is intended to run locally with Docker Compose and the setup scripts in
`setup/`. The scripts start the host-side VirtualBox API and the Docker services
needed by the selected mode.

Use the scripts for normal local usage. Use the Docker commands directly only
when you want to start services step by step for debugging.

## Requirements

- Docker
- Docker Compose
- A configured `.env` file
- VirtualBox installed on the host if dynamic analysis is used
- NVIDIA runtime if you use the provided Ollama GPU container

The frontend runs inside Docker in local Vite development mode, so Node.js and
npm are not required on the host for normal usage.

## Recommended Startup

Run commands from the AIM repository root.

On Linux or WSL:

```bash
./setup/start.sh
```

On Windows PowerShell:

```powershell
.\setup\start.ps1
```

This starts the host-side VirtualBox Manager API and the default Docker Compose
services.

To start the web interface too:

```bash
./setup/start.sh --backend
```

```powershell
.\setup\start.ps1 -Backend
```

This starts the backend and frontend Docker profiles. The web UI is exposed at:

```text
http://localhost:5173
```

To start the backend without the frontend:

```bash
./setup/start.sh --backend --no-frontend
```

```powershell
.\setup\start.ps1 -Backend -NoFrontend
```

## Stop AIM

On Linux or WSL:

```bash
./setup/stop.sh
```

On Windows PowerShell:

```powershell
.\setup\stop.ps1
```

The stop scripts stop Docker Compose services and the tracked host-side
VirtualBox Manager API process.

## Started Services

| Service | Where it runs | Started by | Purpose | Endpoint |
| --- | --- | --- | --- | --- |
| `setup.api` | Host | `setup/start.sh`, `setup/start.ps1` | Controls VirtualBox VMs for dynamic analysis | `http://localhost:8090` |
| `aim` | Docker | Default Compose services | CLI/runtime container with AIM tools | None |
| `ollama` | Docker | Default Compose services | Local model runtime | `http://localhost:11434` |
| `backend` | Docker | `--backend` / `-Backend` | FastAPI web backend | `http://localhost:8000` |
| `frontend` | Docker | `--backend` / `-Backend`, unless frontend is disabled | React/Vite web UI | `http://localhost:5173` |

Host-side runtime state is stored in `.aim-runtime/`. Host-side logs are written
to `logs/`. Docker service logs are available through:

```bash
docker compose logs
```

The VirtualBox Manager API dependencies are installed from
`setup/requirements.txt` into a setup-local virtual environment:

| Host runner | Virtual environment |
| --- | --- |
| Bash / WSL / Linux | `setup/.venv-linux/` |
| PowerShell / Windows | `setup/.venv-windows/` |

## Manual Docker Steps

Use these commands if you do not want the setup scripts to orchestrate the
runtime.

If you need dynamic analysis, start the host-side VirtualBox Manager API before
running the dynamic phase:

```bash
python3 -B -m setup.api
```

On Windows, use the Python launcher if needed:

```powershell
py -3 -B -m setup.api
```

Start the core CLI/runtime services:

```bash
docker compose up -d --build
```

Enter the AIM runtime container:

```bash
docker exec -it aim sh
```

Run a CLI analysis from inside the container:

```bash
python main.py static samples/sample.exe --tool full
```

Start backend and frontend manually:

```bash
docker compose --profile backend --profile frontend up -d --build
```

Start only the backend profile:

```bash
docker compose --profile backend up -d --build
```

Stop all Compose services, including optional profiles:

```bash
docker compose --profile backend --profile frontend down
```

Inspect logs:

```bash
docker compose logs aim
docker compose logs backend
docker compose logs frontend
docker compose logs ollama
```

## When to Use Manual Commands

Use direct Docker commands when:

- you want to rebuild or inspect one service;
- you are debugging Compose profiles;
- you want to run CLI-only analysis from the `aim` container;
- you do not need the host-side VirtualBox API started by the setup scripts.

For local development details, see [Development](../development/README.md).
