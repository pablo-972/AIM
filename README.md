# AIM - AI Malware Analysis

AIM is a modular malware-analysis CLI that combines deterministic static and
radare2-based tools with AI-assisted analysis.

Each sample is identified by SHA-256 and receives an isolated output directory:

```text
output/<sample-sha256>/
```

> Analyze untrusted samples only inside an isolated environment.

## Features

- Static analysis: file type, hashes, metadata, packer detection, strings, PE
  data, and VirusTotal.
- Manual reverse engineering through radare2 and `r2pipe`.
- Static agent for detecting victim-facing threat actor messages.
- Queue-driven reversing agent focused on executable code and assembly.
- Incremental enrichment and malware report generation.
- Ollama, OpenAI, and Gemini model profiles.

Dynamic analysis is not implemented.

## Documentation

- [Orchestrator and runners](docs/orchestrator-and-runners.md)
- [Manual analysis tools](docs/manual-tools.md)
- [Static agent](docs/static-agent.md)
- [Reversing agent](docs/reversing-agent.md)

## Installation

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Static tools may require `file`, `strings`, `exiftool`, and `upx`.
Reverse-engineering tools require radare2 and `r2pipe`.

For Docker:

```bash
docker compose up -d --build
docker exec -it aim bash
```

Copy `.env.example` to `.env`, then configure the providers you use. Model
profiles are defined in `ai/model_profiles.yaml`.

## Quick Start

Run all static tools:

```bash
python main.py static samples/sample.exe --mode full
```

Run selected static tools:

```bash
python main.py static samples/sample.exe --mode file --mode hash --mode strings
```

Run the static strings agent:

```bash
python main.py static samples/sample.exe --mode strings --agent
```

Run manual reversing:

```bash
python main.py reversing samples/sample.exe --mode disasm --function main
python main.py reversing samples/sample.exe --mode import-xrefs --value kernel32.dll
```

Run the reversing agent:

```bash
python main.py reversing samples/sample.exe --agent --depth 12
```

Run the complete implemented pipeline:

```bash
python main.py full samples/sample.exe
```

The `full` phase runs all static tools, the static agent, enrichment, the
manual reversing `full` set, and finally the reversing agent.

Generate enrichment and a report:

```bash
python main.py enrichment samples/sample.exe
python main.py report samples/sample.exe
```

Use `python main.py <phase> -h` to inspect all options.

## Main Artifacts

Depending on the selected workflows, AIM creates:

```text
output/<sample-sha256>/
|-- analysis.json
|-- static_agent.json
|-- threat_actor_messages.json
|-- reversing_agent.json
|-- enrichment.md
`-- report.md
```

`analysis.json` is updated additively by phase and tool. Agent traces keep
steps compact; large data remains in dedicated artifacts or is summarized.

## Configuration

`ai/model_profiles.yaml` maps:

```text
agent or task -> profile -> provider
```

Supported provider types are Ollama, OpenAI, and Gemini. Provider URLs, API
keys, and cloud model names are read from environment variables.

## License

See [LICENSE](LICENSE).
