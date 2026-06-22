# Static Agent

The static agent identifies explicit victim-facing threat actor messages inside
extracted strings.

It is deliberately narrow. It does not attempt to classify all strings or
produce a general malware verdict.

## Running the Agent

The agent requires the `strings` tool or `full`:

```bash
python main.py static sample.exe --mode strings --agent
python main.py static sample.exe --mode full --agent --profile local-static
```

Supported profiles:

- `local-static`
- `openai-static`
- `gemini-static`

## Workflow

```text
StaticToolRunner
    |
    `-- parsed_strings
            |
            v
StaticAgentRunner
    |
    +-- split into chunks of 80 strings
    +-- request a structured decision
    +-- optionally save the complete original chunk
    `-- record a compact step
```

For each chunk, the agent chooses:

- `none`
- `save_threat_actor_messages`

The model never reconstructs or selects individual lines for persistence. If a
chunk is relevant, the tool runner saves the complete original strings block.

This preserves evidence exactly as supplied to the agent.

## Inclusion Rules

The agent focuses on human-readable communication intended for a victim:

- Ransom notes.
- Payment instructions.
- Contact details used for negotiation.
- Decryption instructions.
- Threats and warnings.
- Structured extortion sections.

It should ignore API names, DLLs, paths, metadata, random strings, debug text,
and unrelated URLs.

## Artifacts

### `static_agent.json`

Contains the compact execution trace:

```json
{
  "agent": "static_agent",
  "status": "completed",
  "steps": [],
  "findings": [],
  "artifacts": [],
  "queue": [],
  "errors": []
}
```

Each step records:

- A lightweight strings-chunk reference.
- The structured decision.
- Tool status and compact output.
- An optional finding.
- An optional error.

The strings chunk itself is not duplicated inside the step.

### `threat_actor_messages.json`

Contains the full saved blocks:

```json
{
  "artifact_type": "threat_actor_messages",
  "source": "static_agent",
  "items": [
    {
      "id": 1,
      "created_at": "2026-06-23T00:00:00+00:00",
      "chunk_index": 4,
      "message_block": [
        "Your files have been encrypted.",
        "Contact us to recover your data."
      ]
    }
  ]
}
```

Duplicate message blocks are not stored twice.

## Main Components

- `ai/agents/static.py`: prompt and structured model decision.
- `ai/runner/static.py`: chunk loop and memory recording.
- `tools/runner/static.py`: agent-tool dispatch.
- `tools/static/agent.py`: threat actor message persistence.
- `tools/static/agent_tools.json`: model-callable tool definition.
- `ai/runtime/memory.py`: common compact trace format.
