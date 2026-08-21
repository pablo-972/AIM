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
| `info` | Returns binary metadata from Radare2 | Establishes basic reversing context |
| `entrypoints` | Lists binary entrypoints with file and virtual addresses | Provides execution-start pivots for `disasm --address` |
| `imports` | Lists imported libraries and APIs | Reveals API capabilities and likely behavior |
| `sections` | Lists binary sections with addresses, sizes, and permissions | Provides section-level navigation pivots such as `.text` or `.data` |
| `inspect-section` | Summarizes one selected section without dumping it fully | Separates code, data, and resource pivots by section permissions |
| `functions` | Lists discovered functions | Provides the navigation surface for deeper analysis |
| `details` | Returns details for one selected function | Gives quick function context before full disassembly |
| `strings` | Lists strings visible to the reversing backend | Provides pivots for xrefs and behavior clues |
| `disasm` | Returns disassembly for a selected function | Lets the analyst inspect code behavior directly |
| `address-xrefs` | Finds references to one exact address | Helps inspect jumps, data references, and non-call pivots |
| `string-xrefs` | Finds code references to a selected string | Turns string pivots into executable-code locations |
| `import-xrefs` | Finds code references to a selected import | Turns API pivots into executable-code locations |
| `callers` | Lists callers of a selected function | Shows incoming control flow |
| `callees` | Lists callees of a selected function | Shows outgoing control flow |

The code-oriented manual tools (`details`, `disasm`, `callers`, and `callees`)
accept either `--function` for an internal Radare2 function name or `--address`
for a code address. Use `--address` for values such as `0x401000`, or
`fcn.00401000`. The options are mutually exclusive.

`inspect-section` accepts `--section` and returns a bounded overview. Executable
sections include function counts and a short disassembly preview; data and
resource sections focus on metadata and string previews.

## Agent-Callable Tools

| Tool | Purpose |
| --- | --- |
| `disassembly` | Return structured disassembly instructions for one internal code address |
| `callers` | Return incoming calls for one internal code address |
| `callees` | Return outgoing calls for one internal code address |
| `inspect_section` | Inspect one binary section without dumping it fully |
| `string_xrefs` | Find strings and their code references |
| `import_xrefs` | Find imports and their code references |
| `list_imports` | List imports for focused discovery |
| `list_functions` | List internal functions for focused discovery |
| `list_sections` | List sections with addresses, sizes, and permissions |
| `list_entrypoints` | List recognized entrypoints |

The reversing agent uses these tools through a priority queue. The JSON contract
limits what the model can ask for and validates parameters before execution.
Imported APIs are investigated with `import_xrefs`; the agent then follows a
returned caller address into the sample's code.

Model-proposed targets are normalized before they enter the queue. Address-like
values are routed to code-address tools, section names to `inspect_section`,
imports and DLL names to `import_xrefs`, and arbitrary text to `string_xrefs`.
Normal valid targets are recorded compactly as `validation: "VALID"` in
`reversing_agent.json`; corrected or rejected targets keep a small validation
object with the original and corrected target where applicable.

Generic xrefs are intentionally split by use case:

- `string_xrefs` pivots from specific strings into code.
- `import_xrefs` pivots from imported APIs or DLL names into code.
- `address-xrefs` is manual-only and is useful when an analyst needs references
  to an exact address, for example jump targets or data references.

## Related Phase

See [Reverse engineering](../phases/reversing.md).
