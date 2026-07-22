# Tools

AIM tools are deterministic collectors and analyzers. They gather evidence that
later phases can parse, enrich, send to a model, or include in a report.

Tools are grouped by analysis phase under:

```text
core/tools/
    static/
    dynamic/
    reversing/
```

## Implementation Pattern

Most tool phases follow the same shape:

```text
core/tools/<phase>/
    analyzers/
    manual.py
    agent.py
    *_tools.json
```

Not every phase needs every file.

| Component | Purpose |
| --- | --- |
| `analyzers/` | Low-level implementation of the actual analyzer or parser |
| `manual.py` | Mapping used by manual/CLI execution and deterministic runners |
| `agent.py` | Mapping used when an AI agent can call tools from that phase |
| `*_tools.json` | Tool schema/contract passed to the model for agent-callable tools |

`manual.py` is for tools the analyst or pipeline executes directly. It maps a
short tool name to the Python function that implements it.

`agent.py` is only needed when a model is allowed to call tools during a phase.
It exposes a separate mapping because model-callable tools usually need a
stricter and smaller interface than manual tools.

If a phase exposes tools to an agent, the model receives a JSON tool contract.
The current reversing agent uses:

```text
core/tools/reversing/agent_tools.json
```

This is the current local contract until the project migrates that layer to MCP.

## Static Tools

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

## Dynamic Tools

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

## Reversing Tools

Reversing tools live in:

```text
core/tools/reversing/
```

Manual reversing tools are registered in:

```text
core/tools/reversing/manual.py
```

Agent-callable reversing tools are registered in:

```text
core/tools/reversing/agent.py
```

The model-facing contract is:

```text
core/tools/reversing/agent_tools.json
```

Manual tools:

| Tool | Purpose | Why it is used |
| --- | --- | --- |
| `info` | Returns binary summary information | Establishes basic reversing context |
| `imports` | Lists imported libraries and APIs | Reveals API capabilities and likely behavior |
| `functions` | Lists discovered functions | Provides the navigation surface for deeper analysis |
| `strings` | Lists strings visible to the reversing backend | Provides pivots for xrefs and behavior clues |
| `disasm` | Returns disassembly for a selected function | Lets the analyst inspect code behavior directly |
| `xrefs` | Returns references around a selected function | Helps understand code relationships |
| `string-xrefs` | Finds code references to a selected string | Turns string pivots into executable-code locations |
| `import-xrefs` | Finds code references to a selected import | Turns API pivots into executable-code locations |
| `callers` | Lists callers of a selected function | Shows incoming control flow |
| `callees` | Lists callees of a selected function | Shows outgoing control flow |

Agent-callable tools:

| Tool | Purpose |
| --- | --- |
| `function` | Inspect one function with compact metadata and instructions |
| `disassembly` | Return bounded text disassembly for one function |
| `callers` | Return incoming calls for one function |
| `callees` | Return outgoing calls for one function |
| `string_xrefs` | Find strings and their code references |
| `import_xrefs` | Find imports and their code references |

The reversing agent uses these tools through a priority queue. The JSON contract
limits what the model can ask for and validates parameters before execution.

## Adding a Tool

To add a manual deterministic tool:

1. Add the implementation under `core/tools/<phase>/analyzers/`.
2. Register the tool name in `core/tools/<phase>/manual.py`.
3. Make sure the phase runner can resolve the tool name.
4. Return JSON-serializable data.

To add an agent-callable tool:

1. Add or reuse an analyzer implementation.
2. Register a small model-safe wrapper in `agent.py`.
3. Add the parameter contract to the phase tool JSON file.
4. Validate that the agent runner can execute and record the tool result.

Keep analyzer functions focused on collection or parsing. Put AI prompting,
summarization, and interpretation in the AI layer, not in tools.
