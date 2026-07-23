# Dynamic Tools

Dynamic tools live in:

```text
core/tools/dynamic/
```

Registered in:

```text
core/tools/dynamic/manual.py
```

Dynamic tools are different from static tools because collection happens inside
the malware lab. AIM writes a `job.json` into the execution shared folder, the
Windows agents collect artifacts, REMnux receives them, and Docker parses the
results after collection.

| Tool | Purpose | Why it is used |
| --- | --- | --- |
| `autoruns` | Captures Autoruns before/after snapshots as CSV | Detects startup and persistence changes |
| `registry` | Exports selected registry keys before/after with `reg.exe` | Detects persistence and configuration changes in important keys |
| `procmon` | Captures Procmon activity and converts it to CSV | Shows process, filesystem, registry, and network behavior during execution |

Dynamic analyzers also include job builders and parsers. Their job builders
describe what the Windows monitor should run. Their parsers normalize returned
artifacts into compact JSON suitable for `analysis.json` and dynamic inference.

## Related Setup

- [Dynamic analysis phase](../phases/dynamic.md)
- [Malware lab](../getting-started/malware-lab.md)
- [Software agents](../getting-started/software-agents.md)
