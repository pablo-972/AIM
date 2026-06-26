# Reversing Agent

The reversing agent performs a bounded, queue-driven investigation focused on
executable code and assembly evidence.

Strings, imports, and enrichment are investigation pivots. Findings about
malicious behavior should come from functions, callers, callees, or
disassembly.

## Running the Agent

```bash
python main.py reversing sample.exe --agent --max-targets 12
python main.py reversing sample.exe --agent --profile local-reversing --max-targets 20
```

Supported profiles:

- `local-reversing`
- `openai-reversing`
- `gemini-reversing`

`--max-targets` limits the number of unique queued targets executed. A tool result may
produce several trace steps when its output is divided into chunks.

Manual reversing modes cannot be combined with `--agent`.

## Initialization

If `enrichment.md` exists and contains meaningful content, the agent uses it to
create the initial queue.

If enrichment is unavailable, AIM runs bounded reconnaissance and collects:

- Suspicious imports.
- Large functions.
- Interesting strings.

If the initial model call fails or returns no useful targets, deterministic
reconnaissance targets are used as a fallback.

## Investigation Loop

```text
initial targets
      |
      v
priority queue
      |
      v
execute highest-priority unvisited target
      |
      v
summarize and chunk tool output
      |
      v
agent evaluates evidence
      |
      +-- finding
      +-- no action / finish
      `-- one follow-up target
```

The queue:

- Orders targets by priority.
- Deduplicates queued and visited targets.
- Records every addition and removal in the trace.
- Treats repeated disassembly requests for the same function as one target.

## Agent Tools

| Tool | Purpose |
| --- | --- |
| `string_xrefs` | Locate code references to a string. |
| `import_xrefs` | Locate references to a DLL or imported API. |
| `function` | Perform a lightweight function inspection. |
| `disassembly` | Return bounded text assembly for a function. |
| `callers` | Trace incoming function calls. |
| `callees` | Trace outgoing function calls. |

After useful xrefs, the normal first step is `function`. The agent requests
`disassembly` only when the function contains meaningful instructions, calls,
control flow, loops, API use, or data manipulation worth deeper inspection.

Very small import thunks are not treated as critical code regions.

## Parameter and Context Controls

Tool parameters are normalized before execution:

- Target priority is restricted to `1..100`.
- `disassembly.max_instructions` is restricted to `25..500`.
- Invalid or unknown parameters are rejected.

The disassembly analyzer applies the instruction limit again as a final safety
boundary.

Large xref collections, instruction lists, and disassembly strings are divided
recursively. Each reversing evidence chunk is limited to 4,500 JSON characters.

The evidence prompt also uses bounded enrichment and compact tool definitions.
If the first model response is empty or invalid, AIM retries the same evidence
chunk without enrichment context.

## Findings

The postprocessor rejects findings that are not grounded in executable code.

In particular:

- String and import searches are pivots, not final code findings.
- Empty instruction results cannot produce code conclusions.
- Functions with fewer than three instructions do not produce findings.
- Function names and address ranges are normalized from actual tool output.
- Critical regions require function, caller/callee, xref, or disassembly
  evidence.

## Trace Format

The output is stored in `reversing_agent.json`:

```json
{
  "agent": "reversing_agent",
  "status": "completed",
  "steps": [],
  "findings": [],
  "artifacts": [],
  "queue": [],
  "errors": []
}
```

`steps` contains compact tool metadata such as:

- Function and resolved function.
- Match and xref counts.
- Instruction counts.
- Returned instruction count.
- Truncation status.
- Start and end addresses.

Full disassembly and large collections are not stored directly in step output.

`queue` is an event history:

```json
{
  "event": 3,
  "action": "added",
  "source": "follow_up",
  "target": {
    "tool": "function",
    "parameters": {
      "function": "fcn.401000"
    },
    "priority": 80,
    "reason": "Follow code evidence."
  },
  "queue_size": 2
}
```

## Main Components

- `ai/agents/reversing.py`: prompts and structured decisions.
- `ai/runner/reversing.py`: workflow composition and lifecycle.
- `ai/runtime/reversing_initialization.py`: enrichment/reconnaissance initialization.
- `ai/runtime/reversing_evidence.py`: chunk evaluation and compact retry.
- `ai/runtime/reversing_exploration.py`: bounded queue-execution loop.
- `ai/runtime/reversing_targets.py`: target normalization and queue events.
- `ai/runtime/priority_queue.py`: priority and visited-state management.
- `utils/preprocessing/reversing.py`: bounded recursive chunking.
- `utils/postprocessing/reversing/`: observation, action, finding, and trace policies.
- `tools/reversing/agent.py`: model-callable reversing operations.
- `tools/reversing/agent_tools.json`: tool parameter contract.
- `ai/runtime/memory.py`: compact trace persistence.
