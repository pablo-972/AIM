# Troubleshooting

This section is reserved for known operational issues and fixes.

Keep troubleshooting separate from the main setup flow so the Getting Started
guide remains focused.

## Categories

- [Frontend](#frontend)
- [Agents](#agents)
- [INetSim](#inetsim)

## Frontend

Common symptoms:

- `npm install` fails inside WSL.
- Dependency installation gets stuck or fails with package lifecycle script
  errors.
- `node_modules/` ends up in a broken state after a failed install.

The quickest fix is usually to remove the local install state and retry without
package scripts:

```bash
cd frontend
rm -rf node_modules/
rm -rf node_modules package-lock.json
npm cache clean --force
npm cache verify
npm install --ignore-scripts --verbose
```

If the install still fails, repeat the cleanup and use more verbose npm logging:

```bash
npm install --ignore-scripts --loglevel=silly
```

On some WSL setups this may need to be repeated more than once before npm
rebuilds a clean dependency tree.

## Agents

Common symptoms:

- Windows collector does not start.
- Windows monitor is not running.
- REMnux receiver does not receive artifacts.
- Scheduled tasks do not run as expected.
- The collector moves or launches the malware sample, but the monitor does not
  fully execute.

Checks:

- Verify Windows scheduled tasks.
- Verify the REMnux receiver process.
- Verify the internal network route from Windows to REMnux.
- Verify shared folder availability.

The REMnux-side software agent is usually stable. Most runtime issues happen on
the Windows side when scheduled tasks start Python processes in a way that the
sample later disrupts.

Runtime recovery:

1. Open Task Manager on the Windows VM.
2. Find Python processes started by the Windows scheduled task engine.
3. Terminate those Python processes.
4. Run `start.bat`.
5. Run `collector.py`.

Running the monitor from its own `cmd.exe` process avoids cases where malware
terminates Python child processes launched from the scheduled task chain.

## INetSim

Known REMnux builds can start INetSim while the DNS child process immediately
dies. Typical symptoms:

- INetSim reports `dns_53_tcp_udp` as started.
- DNS lookups from the Windows VM return no response.
- HTTP, HTTPS, and SMTP simulation still work.
- The issue points to INetSim's old `Net::DNS` usage and low-port binding
  behavior.

Minimal fix steps:

1. Stop and disable `systemd-resolved` so port 53 is free:

```bash
sudo systemctl stop systemd-resolved
sudo systemctl disable systemd-resolved
sudo rm /etc/resolv.conf
echo "nameserver 127.0.0.1" | sudo tee /etc/resolv.conf
```

2. Back up INetSim's DNS module:

```bash
sudo cp /usr/share/perl5/INetSim/DNS.pm /usr/share/perl5/INetSim/DNS.pm.bak
```

3. Replace the old DNS loop and remove the duplicated `start_server` call:

```bash
sudo sed -i 's/\$server->main_loop/\$server->start_server;\n    while(1) { \$server->loop_once(10); }/' /usr/share/perl5/INetSim/DNS.pm
sudo sed -i '/\$server->start_server;/d' /usr/share/perl5/INetSim/DNS.pm
```

4. Allow low-port binding for the INetSim user:

```bash
sudo sysctl -w net.ipv4.ip_unprivileged_port_start=0
echo "net.ipv4.ip_unprivileged_port_start=0" | sudo tee -a /etc/sysctl.conf
```

5. Restart INetSim and verify DNS from the Windows VM.

For more context and the full explanation, see:

- [Fixing INetSim DNS on REMnux](https://github.com/Seth-Smithey/Malware_Lab/blob/main/inetsim-dns-fix.md)
