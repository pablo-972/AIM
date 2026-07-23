# Reversing Tools

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

## Manual Tools

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

## Agent-Callable Tools

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

## Related Phase

See [Reverse engineering](../phases/reversing.md).
