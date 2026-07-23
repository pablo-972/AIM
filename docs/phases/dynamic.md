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

## Related Tools

See [Dynamic tools](../tools/dynamic.md).
