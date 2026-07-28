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

It incrementally updates the analyst report body and then performs a final
structured pass.

Input batching depends on the selected report profile:

- local SLM profiles process the prepared evidence in smaller chunks;
- cloud profiles such as Gemini and OpenAI group evidence by phase to reduce the
  number of API calls.

For cloud profiles, the report runner normally sends up to four grouped update
sources before the final structured assessment pass:

- static;
- dynamic;
- enrichment;
- reversing.

Final outputs:

```text
report.md
assessment.json
```

`report.md` is the final analyst-facing document. It summarizes the sample,
preserves important evidence, explains observed behavior, and connects the
static, dynamic, enrichment, and reverse engineering results into one technical
narrative.

`assessment.json` is the machine-readable final verdict used for metrics and
automation. It contains only the compact assessment object:

```json
{
  "is_malware": true,
  "malware_confidence": 0.92,
  "family": "AgentTesla",
  "family_confidence": 0.78,
  "categories": [
    "credential_stealer",
    "keylogger"
  ],
  "summary_reason": "The strongest evidence supports credential theft behavior."
}
```

`family` is reserved for a concrete malware family or malicious tool name that
is identifiable from code, behavior, artifacts, or known naming. Examples:
`AgentTesla`, `Emotet`, `TrickBot`, `QakBot`, `RedLine`, `AsyncRAT`, `LockBit`,
or `DarkGate`.

If only a broad malware type is supported, `family` should be `null`.

`categories` describes malware types, objectives, or main capabilities. Examples:
`ransomware`, `credential_stealer`, `information_stealer`, `keylogger`,
`remote_access_trojan`, `downloader`, `dropper`, `backdoor`, `spyware`, `bot`,
`banking_trojan`, `wiper`, `cryptominer`, or `loader`.

Incremental report updates must return Markdown only. The final model call uses
structured output. For Ollama, AIM sends the report schema through the
`/api/chat` `format` field. For cloud providers, AIM sends the schema through
the provider-specific structured-output mechanism.

The final model response is one JSON object with `report_markdown` and
`assessment`. AIM validates `assessment`, normalizes the Markdown
`Final Assessment` section programmatically, and writes the two files
separately.

The Markdown report does not include the raw JSON assessment.

## Related AI

See [AI](../ai/README.md).
