# AIM - AI Malware Analysis

AIM is a modular malware-analysis CLI that combines deterministic tooling with
AI-assisted analysis.

Each sample is identified by its SHA-256 hash and receives an isolated artifact
directory. Static and reverse-engineering tools produce normalized JSON results,
while AI workflows maintain enrichment and report documents from the available
evidence.

> Run untrusted samples only inside an isolated analysis environment. AIM reads
> potentially malicious files and invokes external analysis tools.

## Current Capabilities

- Static analysis with file identification, hashes, metadata, packer heuristics,
  strings, PE inspection, and VirusTotal.
- AI-assisted inspection of extracted strings for victim-facing threat actor
  messages.
- Manual reverse-engineering queries backed by radare2 through `r2pipe`.
- Incremental reverse-engineering enrichment generated from saved static
  artifacts.
- Incremental malware report generation from static results, actor messages,
  and enrichment notes.
- Local models through Ollama.
- OpenAI and Gemini through OpenAI-compatible chat-completions endpoints.

Dynamic analysis is not implemented.

## Project Structure

```text
.
|-- main.py                         # CLI entry point
|-- cli/                            # Phase parsers and argument validation
|-- orchestrator/
|   |-- context.py                  # Validated, normalized execution context
|   `-- orchestrator.py             # Phase coordination
|-- tools/
|   |-- results.py                  # ToolResult and CommandResult contracts
|   |-- runner/                     # Static and reversing tool runners
|   |-- static/
|   |   |-- analyzers/              # Deterministic static analyzers
|   |   |-- manual.py               # Manual static-tool registry
|   |   |-- agent.py                # Static agent-callable operations
|   |   `-- agent_tools.json        # Static agent tool definitions
|   `-- reversing/
|       |-- analyzers/              # r2pipe session and reversing operations
|       |-- manual.py               # Manual reversing-tool registry
|       |-- agent.py                # Reversing agent-callable operations
|       `-- agent_tools.json        # Reversing agent tool definitions
|-- ai/
|   |-- agents/                     # Agent prompts and decisions
|   |-- generators/                 # Report and enrichment generators
|   |-- providers/                  # Ollama and cloud provider clients
|   |-- runner/                     # AI workflow runners
|   |-- runtime/                    # Agent execution, validation, and memory
|   |-- model_registry.py           # Agent/task to profile/provider resolution
|   `-- model_profiles.yaml         # Providers, profiles, agents, and tasks
|-- utils/
|   |-- artifacts/                  # JSON builder, extractor, Markdown document
|   |-- io/                         # JSON, YAML, text, and command helpers
|   `-- preprocessing/              # Model-friendly evidence preparation
|-- config/                         # Paths, filenames, and environment loading
|-- samples/                        # Optional local sample directory
`-- output/                         # Generated artifacts, grouped by sample hash
```

## Installation

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

Static analysis expects these external programs to be available when their
corresponding analyzer is used:

- `file`
- `strings`
- `exiftool`
- `upx`

Reverse-engineering commands require radare2 and the Python `r2pipe` package.

The repository also includes a Docker environment:

```bash
docker compose up -d --build
docker exec -it aim bash
```

## Configuration

Copy the environment template and configure the providers you intend to use:

```bash
cp .env.example .env
```

Model configuration lives in `ai/model_profiles.yaml` and is divided into:

- `providers`: connection and credential configuration.
- `profiles`: provider, model, temperature, token budget, and response format.
- `agents`: default profiles for agentic workflows.
- `tasks`: default profiles for report and enrichment generation.

Relevant environment variables include:

- `OLLAMA_BASE_URL`
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_STATIC_MODEL`
- `OPENAI_REPORT_MODEL`
- `OPENAI_ENRICHMENT_MODEL`
- `GEMINI_API_KEY`
- `GEMINI_BASE_URL`
- `GEMINI_STATIC_MODEL`
- `GEMINI_REPORT_MODEL`
- `GEMINI_ENRICHMENT_MODEL`
- `VT_API_BASE_URL`
- `VT_API_KEY`

Empty cloud model values are rejected when the selected profile is created.

## CLI

General command shape:

```text
python main.py <phase> <sample> [phase options]
```

Available phases:

- `static`
- `reversing`
- `enrichment`
- `report`

Show the global or phase-specific help:

```bash
python main.py -h
python main.py static -h
python main.py reversing -h
python main.py enrichment -h
python main.py report -h
```

Common options:

- `--output`: base artifact directory. Defaults to `output`.
- `--format json|text`: persist JSON results or print tool results as formatted
  JSON text. Defaults to `json`.

The actual output directory is always:

```text
<output>/<sample-sha256>/
```

## Static Analysis

Run every registered static analyzer:

```bash
python main.py static samples/sample.exe full
```

Run selected analyzers:

```bash
python main.py static samples/sample.exe file hash strings pe
```

Available static modes:

- `file`
- `hash`
- `metadata`
- `packer`
- `strings`
- `vt`
- `pe`
- `full`

`full` cannot be combined with other modes.

Run the static strings agent:

```bash
python main.py static samples/sample.exe strings --agent --profile local-static
```

The static agent requires `strings` or `full`, because it consumes
`parsed_strings` generated during the same execution. Supported profiles are:

- `local-static`
- `openai-static`
- `gemini-static`

## Reverse Engineering

Run basic reverse-engineering collection:

```bash
python main.py reversing samples/sample.exe full
```

`full` currently runs:

- `info`
- `imports`
- `strings`

Run individual operations:

```bash
python main.py reversing samples/sample.exe functions
python main.py reversing samples/sample.exe disasm --function main
python main.py reversing samples/sample.exe xrefs --value 0x401000
python main.py reversing samples/sample.exe string-xrefs --value "example.com"
python main.py reversing samples/sample.exe callers --function sym.main
python main.py reversing samples/sample.exe callees --function sym.main
```

Available reversing modes:

- `info`
- `imports`
- `functions`
- `strings`
- `disasm`
- `xrefs`
- `string-xrefs`
- `callers`
- `callees`
- `full`

The reversing agent tool definitions and dispatcher exist, but the
`reversing --agent` workflow is not yet connected to an AI runner in the
orchestrator.

## Enrichment

Generate or update reverse-engineering enrichment from previously saved static
results and threat actor messages:

```bash
python main.py enrichment samples/sample.exe --profile local-enrichment
```

Supported profiles:

- `local-enrichment`
- `openai-enrichment`
- `gemini-enrichment`

The runner treats `enrichment.md` as a living document. For each prepared
evidence source, the model receives the current body and returns the complete
updated body. The fixed top-level title is:

```markdown
# Reverse Engineering Enrichment
```

The current enrichment runner does not consume saved reversing-phase results.

## Report Generation

Generate or update the malware report:

```bash
python main.py report samples/sample.exe --profile local-report
```

Supported profiles:

- `local-report`
- `openai-report`
- `gemini-report`

The report consumes sources in this order:

1. Saved static tool results.
2. Saved threat actor message blocks.
3. The current reverse-engineering enrichment document, when available.

Large PE and VirusTotal results are reduced or divided into bounded chunks
before being sent to the model. Raw extracted strings are omitted from normal
report input.

Like enrichment, `report.md` is a living document. The model updates the
complete report body after each source while the application preserves the
top-level title:

```markdown
# Malware Analysis Report
```

## Execution Architecture

The runtime flow is:

```text
CLI arguments
    |
    v
AnalysisContext
    |
    v
Orchestrator
    |
    +-- StaticToolRunner ------> analysis.json
    |       |
    |       `-- StaticAgentRunner
    |               +---------> static_agent_steps.json
    |               `---------> threat_actor_messages.json
    |
    +-- ReversingToolRunner ---> analysis.json
    |
    +-- EnrichmentAIRunner ----> enrichment.md
    |
    `-- ReportAIRunner --------> report.md
```

`AnalysisContext` validates that the sample exists, calculates its SHA-256, and
normalizes all CLI values before execution.

`Orchestrator` selects one phase handler and creates shared dependencies lazily.
Tool execution remains in tool runners, model construction remains in
`ModelRegistry`, and artifact-specific behavior remains under
`utils/artifacts`.

## Tool Result Contract

Deterministic tools are normalized through `tools.results.ToolResult`.

Successful result:

```json
{
  "status": "ok",
  "data": {},
  "error": null
}
```

Failed result:

```json
{
  "status": "error",
  "data": null,
  "error": "error message"
}
```

A failing tool does not discard successful results from other selected tools.

## Generated Artifacts

For a sample with SHA-256 `<sha256>`, the default artifact layout is:

```text
output/<sha256>/
|-- analysis.json
|-- static_agent_steps.json
|-- threat_actor_messages.json
|-- enrichment.md
`-- report.md
```

Only artifacts produced by the executed workflows are created.

### `analysis.json`

Static and reversing results share the same phase-based document:

```json
{
  "sample": {
    "path": "/absolute/path/to/sample.exe",
    "sha256": "<sha256>",
    "size": 12345
  },
  "phases": {
    "static": {
      "status": "completed",
      "tools": {
        "hash": {
          "status": "ok",
          "data": {
            "sha256": "<sha256>"
          },
          "error": null
        }
      }
    },
    "reversing": {
      "status": "completed",
      "tools": {}
    }
  }
}
```

`JsonBuilder` loads an existing document and merges incoming tools into the
selected phase. Running one tool later does not replace previously stored tools
or other phases.

### `static_agent_steps.json`

Records each static-agent decision and any tool execution result:

```json
{
  "steps": [
    {
      "step": 1,
      "decision": {
        "thought": "...",
        "action": "save_threat_actor_messages",
        "confidence": "high",
        "parameters": {},
        "chunk_index": 1
      },
      "tool_executed": "save_threat_actor_messages",
      "tool_output": {}
    }
  ]
}
```

### `threat_actor_messages.json`

When the static agent identifies victim-facing communication, AIM stores the
entire original strings chunk rather than reconstructed line-level findings:

```json
{
  "artifact_type": "threat_actor_messages",
  "source": "static_agent",
  "items": [
    {
      "id": 1,
      "created_at": "2026-06-19T00:00:00+00:00",
      "chunk_index": 1,
      "message_block": [
        "Your files have been encrypted.",
        "Contact us to recover your data."
      ]
    }
  ]
}
```

Duplicate blocks are not added again.

## Adding a Static Tool

1. Implement the analyzer under `tools/static/analyzers/`.
2. Register it in `STATIC_MANUAL_TOOLS` inside `tools/static/manual.py`.
3. Add its CLI mode to `STATIC_MODES` in `cli/static_parser.py`.
4. Add preprocessing only when the output is too large or poorly shaped for
   model consumption.
5. If an agent must call it, expose a separate agent operation and declare its
   schema in `tools/static/agent_tools.json`.

The runner wraps normal analyzer output in `ToolResult`; analyzers should return
useful data or raise an exception.

## Adding a Reversing Tool

1. Implement the operation under `tools/reversing/analyzers/`.
2. Register the manual operation in `tools/reversing/manual.py`.
3. Add its CLI mode and required argument validation in
   `cli/reversing_parser.py`.
4. If it is agent-callable, register it separately in
   `tools/reversing/agent.py` and `tools/reversing/agent_tools.json`.

Keep the reusable radare2 session boundary in
`tools/reversing/analyzers/session.py`.

## Adding an AI Profile

1. Add or reuse a provider in `ai/model_profiles.yaml`.
2. Add a profile that references that provider.
3. Assign it as an agent/task default or expose it through the appropriate CLI
   profile choices.

`ModelRegistry` resolves:

```text
agent or task -> profile -> provider
```

Provider-specific HTTP behavior belongs in `ai/providers`, not in runners or
generators.

## Adding a Phase

1. Add its parser under `cli/`.
2. Register the parser in `cli/base_parser.py`.
3. Extend `AnalysisContext` with any required normalized values.
4. Add the phase handler in `Orchestrator._get_phase_handlers()`.
5. Implement tool or AI runners outside the orchestrator.
6. Persist structured results through `utils/artifacts`.

The orchestrator should remain a coordinator rather than becoming the
implementation point for tools, providers, or document formatting.

## Known Limitations

- Dynamic analysis is not implemented.
- The reversing agent CLI path is declared but not connected to an AI runner.
- Enrichment currently uses static artifacts and actor-message blocks, not
  reversing-phase results.
- Report and enrichment updates are sequential model calls and may be slow for
  samples with many prepared evidence chunks.
- Cloud requests are non-streaming and use retry and request-interval controls.
- There is currently no automated test suite in the repository.
