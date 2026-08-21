# Static Analysis

Static analysis collects evidence from the sample without executing it. This
includes file metadata, hashes, packer indicators, strings, PE data, and
optional external context.

Outputs are stored under the `static` phase in:

```text
analysis.json
```

## Static Inference

The static inference model focuses on strings that look like natural language.
Its main goal is to detect threat-facing text such as ransom notes, warnings,
payment instructions, intimidation messages, or other human-readable behavior
that may indicate operator intent.

The model receives prepared string chunks and stores structured findings in:

```text
static_inference.json
```

Static inference does not execute tools directly. It consumes the
strings already extracted during static analysis.

The JSON trace is intentionally compact. Each step represents one string chunk,
the model analysis, and an optional finding:

```json
{
  "name": "static_strings_inference",
  "status": "completed",
  "findings_count": 1,
  "steps": [
    {
      "step": 1,
      "input": {
        "type": "strings_chunk",
        "index": 1,
        "total_chunks": 3
      },
      "analysis": {
        "thought": "The chunk contains a victim-facing ransom note.",
        "confidence": "high"
      },
      "finding": {
        "type": "threat_actor_message",
        "category": "ransom_note",
        "confidence": "high",
        "tone": "threatening",
        "summary": "Victim-facing ransomware message detected.",
        "evidence": [
          "FUNKLOCKER DETECTED"
        ]
      },
      "error": null
    }
  ],
  "findings": [
    {
      "step": 1,
      "type": "threat_actor_message",
      "category": "ransom_note",
      "confidence": "high",
      "tone": "threatening",
      "summary": "Victim-facing ransomware message detected.",
      "evidence": [
        "FUNKLOCKER DETECTED"
      ]
    }
  ],
  "errors": []
}
```

`analysis` replaces older agent-style `decision` blocks. There is no tool block
or queue because static inference does not execute tools. Finding evidence is a
minimal list of exact strings selected from the analyzed chunk.

## Related Tools

See [Static tools](../tools/static.md).
