# Dynamic Analysis

Dynamic analysis runs the sample inside the Windows victim VM and collects raw
behavior artifacts through the Windows agents and REMnux receiver.

Diff-oriented artifacts are reduced to meaningful before/after changes, while
runtime behavior artifacts are normalized into compact process, filesystem,
registry, and network sections. The dynamic model reads those prepared sections
and stores behavioral findings.

Dynamic evidence is stored under the `dynamic` phase in:

```text
analysis.json
```

Dynamic model findings are stored in:

```text
dynamic_inference.json
```

## Dynamic Inference

The dynamic inference model looks for behavior rather than raw event volume. It
reads prepared Autoruns, Registry, and Procmon outputs and focuses on changes or
activity that are useful for malware analysis:

- persistence-related diffs;
- process creation or termination;
- file creation, modification, and renaming;
- registry activity;
- network attempts or connections;
- behavior that supports later enrichment and reverse engineering.

The JSON trace mirrors static inference: each step is one prepared dynamic
section or chunk, followed by model analysis and an optional finding. It does
not store the complete Procmon/Autoruns/Registry chunk because those artifacts
already exist in `analysis.json`.

```json
{
  "name": "dynamic_inference",
  "status": "completed",
  "findings_count": 1,
  "steps": [
    {
      "step": 1,
      "input": {
        "source": "procmon",
        "section": "network.connections",
        "index": 1,
        "total_chunks": 1,
        "total_items": 13,
        "selected_count": 13
      },
      "analysis": {
        "thought": "The sample contacted a remote HTTPS endpoint.",
        "confidence": "high"
      },
      "finding": {
        "type": "dynamic_behavior",
        "category": "network_connection",
        "confidence": "high",
        "summary": "The sample communicated with a remote server over TLS.",
        "evidence": [
          "TCP connection to www.server-q01.com:443"
        ],
        "source": {
          "provider": "procmon",
          "section": "network.connections",
          "chunk": 1
        }
      },
      "error": null
    }
  ],
  "findings": [
    {
      "step": 1,
      "type": "dynamic_behavior",
      "category": "network_connection",
      "confidence": "high",
      "summary": "The sample communicated with a remote server over TLS.",
      "evidence": [
        "TCP connection to www.server-q01.com:443"
      ],
      "source": {
        "provider": "procmon",
        "section": "network.connections",
        "chunk": 1
      }
    }
  ],
  "errors": []
}
```

Dynamic `evidence` is a list of short strings. Source metadata is stored in the
finding's `source` field instead of being duplicated inside evidence.

## Related Tools

See [Dynamic tools](../tools/dynamic.md).
