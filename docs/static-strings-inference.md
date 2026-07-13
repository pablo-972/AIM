# Static Strings Inference

The static strings inference identifies explicit victim-facing threat actor messages inside
extracted strings.

It is deliberately narrow. It does not attempt to classify all strings or
produce a general malware verdict.

## Running the Inference

The inference requires the `strings` tool or `full`:

```bash
python main.py static sample.exe --tool strings --ai
python main.py static sample.exe --tool full --ai --profile local-static
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
StaticInferenceRunner
    |
    +-- split into chunks of 80 strings
    +-- request a structured finding
    `-- record a compact step and optional finding
```

For each chunk, the inference returns either `finding=null` or a finding
classification with `category` and `tone`.

The model never reconstructs or selects individual lines for persistence. If a
chunk is relevant, the runner saves the complete original strings block in the
finding `text` field.

This preserves evidence exactly as supplied to the agent.

## Inclusion Rules

The inference focuses on human-readable communication intended for a victim:

- Ransom notes.
- Payment instructions.
- Contact details used for negotiation.
- Decryption instructions.
- Threats and warnings.
- Structured extortion sections.

It should ignore API names, DLLs, paths, metadata, random strings, debug text,
and unrelated URLs.

## Artifacts

### `static_strings_inference.json`

Contains the compact execution trace and threat-actor message findings:

```json
{
  "agent": "static_strings_inference",
  "status": "completed",
  "steps": [
    {
      "step": 1,
      "input": {
        "type": "strings_chunk",
        "index": 1,
        "value": null
      },
      "decision": {
        "thought": "The chunk contains a victim-facing ransom note.",
        "confidence": "high",
        "action": "none",
        "parameters": {}
      },
      "tool": {
        "name": "none",
        "status": "skipped",
        "output": null,
        "artifact_ref": null
      },
      "finding": {
        "type": "threat_actor_message",
        "confidence": "high",
        "text": "Your files have been encrypted.\nContact us to recover your data.",
        "category": "ransom_note",
        "tone": "extortion"
      },
      "error": null
    }
  ],
  "findings": [
    {
      "type": "threat_actor_message",
      "confidence": "high",
      "text": "Your files have been encrypted.\nContact us to recover your data.",
      "category": "ransom_note",
      "tone": "extortion",
      "step": 1
    }
  ],
  "artifacts": [],
  "queue": [],
  "errors": []
}
```

Each step records:

- A lightweight strings-chunk reference.
- The structured decision.
- An optional finding.
- An optional error.

The strings block itself is stored only when there is a finding.

## Main Components

- `ai/inferences/static.py`: prompt and structured model decision.
- `ai/runner/static.py`: chunk loop and memory recording.
- `ai/runtime/memory.py`: common compact trace format.
