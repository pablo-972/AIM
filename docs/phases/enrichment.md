# Enrichment

Enrichment is a model-backed phase that reads the results of earlier phases and
builds a working document for the analyst and the reversing phase.

It reads deterministic outputs and AI findings from static and dynamic analysis,
then updates:

```text
enrichment.md
```

The goal is not to write the final report. The goal is to collect the most
important points of interest before reverse engineering starts:

- suspicious strings;
- behavior patterns;
- dynamic findings;
- likely persistence points;
- interesting network destinations;
- imports or functions worth investigating.

The reverse engineering agent uses this document as the preferred starting
context for its initial investigation queue.

## Related AI

See [AI](../ai/README.md).
