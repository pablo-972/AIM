# Static Tools

Static tools live in:

```text
core/tools/static/
```

Registered in:

```text
core/tools/static/manual.py
```

| Tool | Purpose | Why it is used |
| --- | --- | --- |
| `file` | Identifies file type and basic format information | Confirms what kind of sample is being analyzed |
| `metadata` | Extracts filesystem-level metadata | Provides size and timestamp context |
| `hash` | Calculates hashes | Creates stable identifiers for the sample |
| `packer` | Detects common packing indicators | Helps identify obfuscation or packed binaries |
| `strings` | Extracts readable strings | Feeds analyst review and static strings inference |
| `pe` | Parses PE structure | Exposes imports, sections, headers, and Windows binary structure |
| `vt` | Queries VirusTotal when configured | Adds external reputation and detection context |

Static tools do not execute the sample. They are safe evidence collectors for
the first phase of analysis.

## Related Phase

See [Static analysis](../phases/static.md).
