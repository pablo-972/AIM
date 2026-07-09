# Dynamic analysis setup

The dynamic phase assumes the VM agents are installed and started inside the guest machines. AIM does not copy or execute those agents through VirtualBox Guest Control.

## Host side

Start the VirtualBox host API outside Docker:

```bash
python setup/virtualbox_api.py
```

AIM uses this API to:

- restore the victim snapshot;
- configure the shared folder named `shared`;
- start and stop the victim and analysis VMs.

VM stop operations use a graceful ACPI shutdown first. If a VM does not stop within the configured grace window, the VirtualBox API falls back to a forced `poweroff`. This is used both by `--stop` and by dynamic-run cleanup after a timeout.

The shared folder points to the repository `shared/` directory. AIM writes each job directly in:

```text
shared/
```

The shared directory contains:

- the malware sample;
- `job.json`.

REMnux writes the final dynamic result under:

```text
shared/dynamic_result.json
```

## REMnux analysis VM

Install the collector manually inside REMnux.

Recommended shared mount path:

```text
/home/remnux/aim
```

The collector script is:

```text
tools/dynamic/remnux_collector_api.py
```

Install it inside the VM and run it with a persistent service. A simple systemd unit is the preferred approach:

```bash
sudo nano /etc/systemd/system/aim-remnux-collector.service
```

```ini
[Unit]
Description=AIM REMnux Dynamic Collector
After=network-online.target vboxadd-service.service
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/remnux/aim/agents
ExecStartPre=/bin/sh -c 'for i in $(seq 1 60); do test -f /home/remnux/aim/agents/remnux_collector_api.py && exit 0; sleep 2; done; exit 1'
ExecStart=/home/remnux/aim/agents/env/bin/python /home/remnux/aim/agents/remnux_collector_api.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Before enabling it, create the virtual environment once:

```bash
cd /home/remnux/aim/agents
python3 -m venv env
. env/bin/activate
pip install fastapi uvicorn
```

Then enable the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable aim-remnux-collector
sudo systemctl start aim-remnux-collector

sudo systemctl enable inetsim
sudo systemctl start inetsim
```

The collector listens on:

```text
0.0.0.0:8080
```

## Windows victim VM

Install the Windows agent manually inside the victim VM.

Recommended shared path for automatic/headless execution:

```text
\\VBOXSVR\shared
```

If you run the agent manually after logging in, VirtualBox may also expose the share as `Z:\`, but startup tasks should not depend on that mapped drive.

The recommended Windows agent is the Python one:

```text
tools/dynamic/windows_agent.py
```

It is compatible with Python 3.5.1 and uses only the Python standard library. Copy it into the VM, for example:

```text
C:\AIM\windows_agent.py
```

The helper batch file is:

```text
tools/dynamic/start_windows_agent.bat
```

Copy it as:

```text
C:\AIM\start_windows_agent.bat
```

There is also a PowerShell fallback:

```text
tools/dynamic/windows7_agent.ps1
```

Configure Windows persistence using your preferred method, for example:

- Task Scheduler at system startup;
- a Windows service wrapper;
- a startup folder entry for lab-only usage.

For headless execution, do not depend on a logged-in user. Also avoid using the `Z:\` mapped drive in startup tasks, because mapped drive letters may not exist for `SYSTEM` or before VirtualBox Guest Additions finishes mounting shared folders. Prefer the UNC path:

```text
\\VBOXSVR\shared
```

On Windows 7, the most reliable lab setup is usually:

1. enable automatic login for the analysis user, for example `practicas`;
2. create the task as `ONLOGON` for that user;
3. launch the VM with VirtualBox `--type headless`.

VirtualBox headless mode only means there is no visible VM window. It does not automatically create a Windows user session. If no user logs in and the task is configured as `ONLOGON`, the agent will not start.

Example Task Scheduler action:

```powershell
schtasks /create /tn "AIM Agent" ^
/tr "C:\AIM\start_windows_agent.bat" ^
/sc onstart ^
/ru SYSTEM ^
/rl highest ^
/f
```

If `SYSTEM` cannot access `\\VBOXSVR\shared`, use the auto-login user instead:

```powershell
schtasks /create /tn "AIM Agent" ^
/tr "C:\AIM\start_windows_agent.bat" ^
/sc onlogon ^
/ru practicas ^
/rl highest ^
/f
```

Manual run:

```powershell
C:\Python35\python.exe C:\AIM\windows_agent.py --shared-path \\VBOXSVR\shared
```

If `autorunsc.exe` is not in `PATH`, pass its real full path:

```powershell
C:\Python35\python.exe C:\AIM\windows_agent.py --shared-path \\VBOXSVR\shared --autorunsc C:\Tools\Sysinternals\autorunsc.exe
```

The Python agent writes a local debug log to:

```text
C:\AIM\windows_agent.log
```

The Windows agent watches:

```text
\\VBOXSVR\shared
```

When AIM creates a new `job.json`, the agent performs only this flow:

1. copy the sample to the local working directory as an `.exe`;
2. run one Autoruns capture and send the raw output to REMnux as `before_execution`;
3. execute the sample;
4. wait `collect_interval_seconds` from `job.json`;
5. run one final Autoruns capture and send the raw output to REMnux as `after_execution`;
6. stop the sample process if it is still running.

## Shared folder permissions

AIM configures the VirtualBox shared folder as:

- REMnux analysis VM: read-write;
- Windows victim VM: read-only.

The victim should only read jobs and samples from the shared folder. It should not write the final dynamic result. REMnux owns result aggregation and writes `dynamic_result.json`.
