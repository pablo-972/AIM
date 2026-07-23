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

## Documents

- [Static tools](static.md)
- [Dynamic tools](dynamic.md)
- [Reversing tools](reversing.md)

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
