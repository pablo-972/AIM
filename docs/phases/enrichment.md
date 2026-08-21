# Enrichment

Enrichment is a model-backed phase that reads the results of earlier phases and
builds a working document for the analyst and the reversing phase.

It reads deterministic outputs and AI findings from static and dynamic analysis,
then updates:

```text
enrichment.md
```

Input batching depends on the selected enrichment profile:

- local SLM profiles process grouped phase sources to reduce repeated
  inference while keeping the prompt bounded:
  `static.tools`, `static.inference`, `dynamic.tools`,
  `dynamic.inference`;
- cloud profiles such as Gemini and OpenAI use the same prepared source model
  and group evidence by phase before sending it to the model.

VirusTotal enrichment data is intentionally compact. It keeps the fields that
are useful as reversing context, such as `sandbox_verdicts`, `tags`, and
`last_analysis_stats`, instead of forwarding broad classification-oriented
metadata.

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
