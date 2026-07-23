# Static Analysis

Static analysis collects evidence from the sample without executing it. This
includes file metadata, hashes, packer indicators, strings, PE data, and
optional external context.

Outputs are stored under the `static` phase in:

```text
analysis.json
```

## Static Strings Inference

The static inference model focuses on strings that look like natural language.
Its main goal is to detect threat-facing text such as ransom notes, warnings,
payment instructions, intimidation messages, or other human-readable behavior
that may indicate operator intent.

The model receives prepared string chunks and stores structured findings in:

```text
static_strings_inference.json
```

Static strings inference does not execute tools directly. It consumes the
strings already extracted during static analysis.

## Related Tools

See [Static tools](../tools/static.md).
