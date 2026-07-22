# Dynamic analysis setup

The dynamic phase runs a Windows victim VM and a REMnux analysis VM through the
VirtualBox host API. The Windows side executes the sample and collects raw
artifacts. The REMnux side receives and stores those artifacts.

Dynamic tool output is parsed on the host after the artifacts arrive. The
Windows agent should not analyze tool output.

## Host side

Before running any dynamic phase, start the VirtualBox host API from WSL. Keep
this process running while AIM controls the VMs:

```bash
python3 -B -m setup.api
```

AIM uses this API to:

- restore the victim snapshot;
- configure VirtualBox shared folders;
- start the victim and analysis VMs;
- stop the VMs during cleanup.

The host API exposes two shared-folder sources from `config.settings`:

```text
shared/execution
shared/artifacts
```

The victim VM receives the `execution` folder as read-only. AIM writes the
sample, `job.json`, and optional Procmon `.pmc` filter files there.

The REMnux VM receives the `artifacts` folder as read-write. The receiver writes
tool artifacts there as soon as the Windows tools upload them.

Required environment values:

```text
AIM_VBOXMANAGE_API_HOST
AIM_VBOXMANAGE_API_PORT
AIM_DYNAMIC_VICTIM_VM
AIM_DYNAMIC_VICTIM_SNAPSHOT
AIM_DYNAMIC_ANALYSIS_VM
AIM_DYNAMIC_ANALYSIS_SHARED_MOUNT_POINT
AIM_DYNAMIC_ANALYSIS_BASE_URL
AIM_DYNAMIC_ANALYSIS_TIMEOUT
```

Set the VirtualBox VM names and snapshot in `.env` before running the dynamic
pipeline:

```env
AIM_VBOXMANAGE_API_HOST=host.docker.internal
AIM_VBOXMANAGE_API_PORT=8090

AIM_DYNAMIC_VICTIM_VM=W7X64SP1
AIM_DYNAMIC_VICTIM_SNAPSHOT=Agent
AIM_DYNAMIC_VICTIM_SHARED_PATH=Z:\execution

AIM_DYNAMIC_ANALYSIS_VM=REMnux
AIM_DYNAMIC_ANALYSIS_SHARED_MOUNT_POINT=/home/remnux/AIM

AIM_DYNAMIC_ANALYSIS_BASE_URL=http://192.168.255.1:8080
AIM_DYNAMIC_ANALYSIS_TIMEOUT=10
```

`AIM_DYNAMIC_VICTIM_VM` and `AIM_DYNAMIC_ANALYSIS_VM` must match the VirtualBox
machine names exactly. `AIM_DYNAMIC_VICTIM_SNAPSHOT` must match the snapshot
that AIM restores before executing the sample.

## CLI

Start or stop the configured dynamic VMs:

```bash
python main.py dynamic sample.exe --start
python main.py dynamic sample.exe --stop
```

Run selected dynamic tools:

```bash
python main.py dynamic sample.exe --tool autoruns
python main.py dynamic sample.exe --tool registry --tool procmon
python main.py dynamic sample.exe --tool full --ai
```

Use a Procmon filter configuration:

```bash
python main.py dynamic sample.exe --tool procmon --filter config/ProcmonConfiguration.pmc
python main.py dynamic sample.exe --tool full --filter config/ProcmonConfiguration.pmc
```

The `full` pipeline also runs the dynamic phase before enrichment.

## REMnux analysis VM

Install the receiver manually inside REMnux:

```text
core/tools/dynamic/agents/remnux/receiver.py
```

The current receiver stores artifacts under:

```text
/home/remnux/AIM
```

Configure `AIM_DYNAMIC_ANALYSIS_SHARED_MOUNT_POINT` so the VirtualBox shared
folder named `shared` maps to that path, or adjust the receiver path if your lab
uses another mount point.

Install FastAPI and Uvicorn in the receiver environment:

```bash
python3 -m venv env
. env/bin/activate
pip install fastapi uvicorn
```

Run it manually while testing:

```bash
python receiver.py
```

For persistent execution, use a systemd unit. Example:

```ini
[Unit]
Description=AIM REMnux Dynamic Receiver
After=network-online.target vboxadd-service.service
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/remnux/Receiver
ExecStart=/home/remnux/Receiver/env/bin/python /home/remnux/Receiver/receiver.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable the service and INetSim if your lab uses simulated network services:

```bash
sudo systemctl daemon-reload
sudo systemctl enable aim-remnux-receiver
sudo systemctl start aim-remnux-receiver

sudo systemctl enable inetsim
sudo systemctl start inetsim
```

The receiver listens on:

```text
0.0.0.0:8080
```

## Windows victim VM

Install the Windows agents manually inside the victim VM:

```text
core/tools/dynamic/agents/windows7/monitor.py
core/tools/dynamic/agents/windows7/collector.py
core/tools/dynamic/agents/windows7/start.bat
```

Recommended destination:

```text
C:\AIM
```

The victim reads the shared execution folder through:

```text
\\VBOXSVR\shared
```

Startup tasks should not depend on a mapped drive such as `Z:\`. Mapped drive
letters may not exist for `SYSTEM` or during early boot.

The Windows split is:

- `monitor.py`: long-lived local HTTP service on `127.0.0.1:8765`; it runs
  Autoruns, Registry exports, and Procmon collection.
- `collector.py`: watches `\\VBOXSVR\shared\job.json`, copies the sample to
  `C:\AIM`, launches the sample, and tells the monitor when to collect.

For headless Windows tasks, run them as `SYSTEM` at startup. Recommended task
commands:

```powershell
schtasks /Create /TN Monitor /TR C:\AIM\start.bat /SC ONSTART /RU SYSTEM
```

or, if you prefer to call the Python script directly:

```powershell
schtasks /Create /TN Monitor /TR C:\AIM\monitor.py /SC ONSTART /RU SYSTEM
```

Start the collector after a short delay so the monitor and shared folder have
time to become available:

```powershell
schtasks /Create /TN Collector /TR C:\AIM\collector.py /SC ONSTART /RU SYSTEM /DELAY 0000:05
```

If direct `.py` execution is not associated with Python in the VM, point the
task action to the Python executable explicitly.

## Dynamic tools

Supported dynamic tools:

- `autoruns`: captures `before_execution.csv` and `after_execution.csv`.
- `registry`: exports selected persistence-related registry keys before and
  after execution with `reg.exe export`.
- `procmon`: captures `procmon.pml`, stops Procmon, converts the log to CSV, and
  uploads the CSV.

The monitor uploads artifacts immediately to REMnux. The host waits for the
expected files in `shared/artifacts`, then parses them into the dynamic phase of
`analysis.json`.

When dynamic AI inference is enabled, AIM creates:

```text
output/<sample-sha256>/dynamic_inference.json
```

Those findings are later passed to enrichment and report generation as compact
behavior summaries with supporting evidence.
