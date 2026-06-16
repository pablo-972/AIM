# AIM - AI Malware Analysis

AIM is an AI-assisted malware analysis framework. It runs deterministic analysis tools, stores normalized artifacts, and then lets AI runners generate enrichment notes or a technical report from those artifacts.

The current implementation focuses on static analysis, a static strings agent, reverse-engineering enrichment, and report generation.

Run malware samples only in an isolated environment. AIM reads and enriches potentially malicious artifacts and depends on external analysis binaries.

## Project Layout

```text
.
|-- main.py                         # CLI entry point
|-- cli/                            # Argument parsers and validation
|-- core/                           # Shared context and result contracts
|-- orchestrator/                   # Central phase coordinator
|-- tools/
|   |-- static/                     # Static-analysis tool implementations
|   `-- runner/                     # Tool runners
|-- ai/
|   |-- agents/                     # Agent prompts and agent logic
|   |-- generators/                 # Non-agentic AI generators
|   |-- providers/                  # LLM provider clients
|   |-- runner/                     # AI runners for agents, reports, enrichment
|   |-- runtime/                    # Agent executor, memory, validators
|   `-- model_profiles.yaml         # Provider/profile/task configuration
|-- utils/
|   |-- artifacts/                  # Artifact builders and readers
|   |-- io/                         # Files, text, paths, command execution
|   |-- preprocessing/              # Report/enrichment input preparation
|   `-- logger.py
|-- config/                         # Settings and environment access
|-- samples/                        # Local samples
`-- output/                         # Generated artifacts
```

## Installation

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Static analysis also expects these system tools to be available:

- `file`
- `strings`
- `exiftool`
- `upx`

The repository includes Docker files for a prepared environment:

```bash
docker compose up -d --build
docker exec -it aim bash
```

## Configuration

Model providers and profiles are configured in `ai/model_profiles.yaml`.

Supported provider implementations:

- `ollama`
- `openai` / OpenAI-compatible APIs

The YAML also contains placeholder provider entries for Anthropic and Gemini, but those providers are not implemented in `ai.providers.factory.ProviderFactory` yet.

Common environment variables:

- `OLLAMA_BASE_URL`
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_STATIC_MODEL`
- `OPENAI_REPORT_MODEL`
- `OPENAI_ENRICHMENT_MODEL`
- `VT_API_BASE_URL`
- `VT_API_KEY`

## Usage

Show CLI help:

```bash
python main.py -h
```

Run full static analysis:

```bash
python main.py static /path/to/sample full
```

Run selected static tools:

```bash
python main.py static /path/to/sample file hash strings pe
```

Write artifacts to a custom output directory:

```bash
python main.py static /path/to/sample full --output output
```

Run the static strings agent:

```bash
python main.py static /path/to/sample strings --agent --profile local-static
```

The static agent requires `strings` or `full`, because it consumes extracted `parsed_strings`.

Generate reverse-engineering enrichment from existing artifacts:

```bash
python main.py enrichment /path/to/sample --profile local-enrichment
```

Generate a report from existing static analysis artifacts:

```bash
python main.py report /path/to/sample --module static --profile local-report
```

## Architecture

`main.py` builds the CLI parser, validates CLI arguments when a phase provides a validator, and passes the parsed arguments to `Orchestrator`.

The orchestrator is the central coordinator:

1. Converts CLI arguments into `core.context.AnalysisContext`.
2. Dispatches the selected phase via `PHASE_HANDLERS`.
3. Creates shared dependencies such as `ModelRegistry` and `StaticToolRunner`.
4. Runs deterministic tools, AI agents, enrichment, or reporting as needed.

The implemented phases are:

- `static`: runs static tools, persists `analysis.json`, and optionally runs the static agent.
- `enrichment`: consumes previous artifacts and updates `enrichment.md`.
- `report`: consumes previous artifacts and writes `report.md`.

## Contracts

Shared contracts live under `core/`.

`AnalysisContext` contains the normalized execution context:

- sample path
- output directory
- phase
- output format
- selected profile
- selected static modes
- static-agent flag

`ToolResult` normalizes tool outputs:

```json
{
  "status": "ok",
  "data": {},
  "error": null
}
```

Failures use the same shape:

```json
{
  "status": "error",
  "data": null,
  "error": "error message"
}
```

## Static Tools

Static tools live in `tools/static/` and are registered by `tools.runner.static.StaticToolRunner`.

Available modes:

- `file`: identifies the file type using `file`.
- `hash`: computes `md5`, `sha1`, `sha256`, and PE `imphash` when available.
- `metadata`: extracts metadata with `exiftool -j`.
- `packer`: applies PE packer and entropy heuristics.
- `strings`: extracts strings, filters noise, and extracts IOCs.
- `pe`: extracts PE architecture, sizes, subsystem, sections, imports, exports, delay imports, version info, and resources.
- `vt`: queries VirusTotal for the sample SHA256.
- `full`: runs all registered static tools.

External commands go through `utils.io.commands.run_command`, which adds timeout handling and a shared command-result contract.

## Static Agent

The static agent searches extracted strings for victim-facing threat actor messages, such as:

- ransom notes
- payment instructions
- wallet addresses
- negotiation contact details
- decryption instructions
- threats or anti-law-enforcement instructions

Components:

- `ai.agents.static.StaticAgent`: agent prompt and LLM call.
- `ai.runner.static.StaticAgentRunner`: chunks strings and runs the agent.
- `ai.runtime.executor.AgentStepExecutor`: validates and dispatches tool calls.
- `ai.runtime.memory.AgentMemory`: records agent steps.
- `tools.static.actor_messages.save_threat_actor_messages`: saves selected message blocks.

Agent-callable tools are declared in:

```text
tools/static/tools.json
```

The static agent writes:

```text
output/static_agent_steps.json
output/threat_actor_messages.json
```

## Preprocessing

AI inputs are prepared under `utils/preprocessing/`.

The goal is to avoid sending large raw tool outputs directly to the model.

Current preprocessing behavior:

- `strings`: removes the raw string list from report input and keeps counts/IOCs.
- `pe`: splits report/enrichment input into `summary`, `sections`, and grouped import chunks such as `imports.1`, `imports.2`.
- `vt`: keeps high-signal report chunks and reduces enrichment input to essential classification, sandbox verdicts, tags, meaningful name, and detection stats.
- `threat_actor_messages`: extracts only `items[*].message_block`, filters noisy runtime/error strings, and sends clean actor-message blocks as separate enrichment sources.

## Generated Artifacts

The main artifact is:

```text
output/analysis.json
```

Shape:

```json
{
  "schema_version": "1.0",
  "sample": {
    "path": "/path/to/sample",
    "size": 12345
  },
  "phases": {
    "static": {
      "status": "completed",
      "tools": {
        "hash": {
          "status": "ok",
          "data": {
            "sha256": "..."
          },
          "error": null
        }
      },
      "findings": []
    }
  }
}
```

Additional artifacts:

- `output/static_agent_steps.json`: static-agent decisions and tool outputs.
- `output/threat_actor_messages.json`: selected victim-facing actor messages.
- `output/enrichment.md`: reverse-engineering enrichment notes.
- `output/report.md`: final report generated from saved artifacts.

`threat_actor_messages.json` shape:

```json
{
  "schema_version": "1.0",
  "artifact_type": "threat_actor_messages",
  "source": "static_agent",
  "items": [
    {
      "id": 1,
      "created_at": "2026-06-14T00:00:00+00:00",
      "chunk_index": 1,
      "message_block": []
    }
  ]
}
```

## Report Generation

`ai.runner.report.ReportAIRunner` reads existing artifacts and sends preprocessed chunks to `ai.generators.report.AIReport`.

The report runner writes:

```text
output/report.md
```

For large or noisy tools, the report receives structured chunks rather than full raw JSON blobs.

## Enrichment

`ai.runner.enrichment.EnrichmentAIRunner` incrementally updates reverse-engineering notes from preprocessed sources.

The runner keeps the top-level title fixed:

```markdown
# Reverse Engineering Enrichment
```

The model controls the body structure. It may add, remove, merge, or rename subsections when useful. The runner only sanitizes model output by removing code fences and preventing duplicate top-level titles.

The enrichment runner writes:

```text
output/enrichment.md
```

## Adding a New Static Tool

1. Implement a function in `tools/static/`.
2. Export it from `tools/static/__init__.py`.
3. Register it in `STATIC_TOOL_RUNNERS` inside `tools/runner/static.py`.
4. Add the mode to `STATIC_MODES` in `cli/static_parser.py`.
5. Add preprocessing only if the output is large or needs model-friendly shaping.

Use `ToolResult` through the runner contract; individual tools should return useful data or raise an exception.

## Adding a New Phase

1. Add a parser in `cli/`.
2. Register it in `cli/base_parser.py`.
3. Add a phase handler to `Orchestrator.PHASE_HANDLERS`.
4. Implement the handler method in `orchestrator/orchestrator.py`.
5. Persist phase artifacts using helpers in `utils.artifacts`.

Keep the orchestrator as the central coordinator. AI runners should not execute tools directly; when an AI workflow needs a tool action, route it through the relevant tool runner.

## Current Status

- Static analysis phase implemented.
- Static strings agent implemented.
- Reverse-engineering enrichment implemented.
- Report generation implemented.
- Ollama and OpenAI-compatible providers implemented.
- Dynamic analysis and additional provider backends are not implemented yet.
