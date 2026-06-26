# Orchestrator and Runners

This document describes how AIM routes a CLI request, executes tools or AI
workflows, and persists artifacts.

## Execution Flow

```text
CLI parser
    |
    v
AnalysisContext
    |
    v
Orchestrator
    |
    +-- StaticToolRunner
    +-- ReversingToolRunner
    +-- StaticAgentRunner
    +-- ReversingAgentRunner
    +-- EnrichmentAIRunner
    `-- ReportAIRunner
```

`main.py` builds the parser, validates phase arguments, and creates the
`Orchestrator`.

`AnalysisContext`:

- Resolves and validates the sample path.
- Calculates the sample SHA-256.
- Creates the sample-specific output path.
- Normalizes phase, mode, profile, agent, function, value, and maximum-target options.

The output directory is:

```text
<base-output>/<sample-sha256>/
```

## Orchestrator Responsibilities

`orchestrator/orchestrator.py` is a coordinator. It:

- Selects the requested phase.
- Lazily creates tool runners, the JSON builder, and the model registry.
- Sends manual tool results to `analysis.json`.
- Starts an agent runner only when the relevant `--agent` flag is enabled.

It does not implement analyzers, prompts, provider HTTP requests, or artifact
formatting.

Available phase handlers are:

- `static`
- `reversing`
- `enrichment`
- `report`
- `full`

For static analysis, deterministic tools run before the optional static agent.
The agent receives the `parsed_strings` produced during that execution.

For reversing, manual modes and the reversing agent are mutually exclusive.
The `full` phase is the explicit pipeline exception because it runs them as
separate sequential stages:

```text
static full
    -> static agent
    -> enrichment
    -> reversing full (info, imports, strings)
    -> reversing agent
```

`Orchestrator.run_full_phase()` creates a phase-specific `AnalysisContext` for
each stage and reuses `run_static_phase()`, `run_enrichment_phase()`, and
`run_reversing_phase()`. Reversing is invoked twice with different contexts:
first for manual tools and then for the agent.

The pipeline accepts independent profiles through `--static-profile`,
`--enrichment-profile`, and `--reversing-profile`. Intermediate deterministic
results are always persisted in `analysis.json` because later stages consume
that artifact.

## Tool Runners

`StaticToolRunner` and `ReversingToolRunner` execute registered manual tools.
Each operation is isolated so one failing tool does not discard successful
results from the same phase.

Manual outputs use the `ToolResult` contract:

```json
{
  "status": "ok",
  "data": {},
  "error": null
}
```

On failure:

```json
{
  "status": "error",
  "data": null,
  "error": "error message"
}
```

Agent tool runners use a separate interface:

```json
{
  "success": true,
  "data": {}
}
```

This keeps CLI tools and model-callable tools independent even when they reuse
the same lower-level analyzer.

Reversing agent tool calls pass through `AgentStepExecutor`. Reversing supplies
the validated target removed from its priority queue. The shared executor
validates and normalizes parameters, invokes the phase tool runner, captures
exceptions, and enforces the agent-tool result object contract.

The static agent does not call tools. It classifies strings chunks and stores
victim-facing message findings directly in `static_agent.json`.

## AI Runners

AI runners own workflow state and call agents, tools, and persistence helpers:

- `StaticAgentRunner` processes strings in chunks.
- `ReversingAgentRunner` executes a prioritized investigation queue.
- `EnrichmentAIRunner` updates `enrichment.md`.
- `ReportAIRunner` updates `report.md`.

`ModelRegistry` resolves the selected agent or task profile into a provider
client using `ai/model_profiles.yaml`.

## Artifact Persistence

`JsonBuilder` stores deterministic tool results in `analysis.json`.
Updates are additive:

- Existing phases are preserved.
- Existing tools inside a phase are preserved.
- Rerunning one tool replaces only that tool's current result.

Example:

```json
{
  "sample": {
    "path": "/samples/example.exe",
    "sha256": "<sha256>",
    "size": 12345
  },
  "phases": {
    "static": {
      "status": "completed",
      "tools": {
        "hash": {
          "status": "ok",
          "data": {},
          "error": null
        }
      }
    }
  }
}
```

Agent traces are stored separately because they contain decisions, findings,
queue events, and compact tool-output summaries.

## Adding a Phase

1. Add its parser under `cli/`.
2. Register it in `cli/base_parser.py`.
3. Add normalized fields to `AnalysisContext` when needed.
4. Implement its tool or AI runner outside the orchestrator.
5. Add a phase handler to `Orchestrator`.
6. Persist deterministic results through `JsonBuilder` or use a dedicated
   artifact for agent/document workflows.
