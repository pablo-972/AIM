# Getting Started

This section walks through the minimum setup required to run AIM and prepare a
dynamic malware analysis lab.

Recommended order:

1. Configure the project.
2. Prepare the malware lab.
3. Configure the agents.
4. Choose a deployment mode.

```mermaid
flowchart TD
    Config[Configure .env] --> Lab[Prepare REMnux and Windows 7 lab]
    Lab --> Agents[Install and start software agents]
    Agents --> Deploy[Choose deployment mode]
```

## Documents

- [Configuration](configuration.md)
- [Malware Lab](malware-lab.md)
- [Agents](software-agents.md)
- [Deployment](deployment.md)



