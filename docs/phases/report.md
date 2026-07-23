# Report

The report phase is similar to enrichment in the way it consumes previous
outputs, but its purpose is different.

Report generation reads:

- deterministic static evidence;
- static inference findings;
- dynamic parsed artifacts;
- dynamic inference findings;
- enrichment notes;
- reversing agent findings.

It incrementally updates:

```text
report.md
```

The report phase is the final analyst-facing document. It should summarize the
sample, preserve important evidence, explain observed behavior, and connect the
static, dynamic, enrichment, and reverse engineering results into one technical
narrative.

## Related AI

See [AI](../ai/README.md).
