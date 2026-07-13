# Manual Analysis Tools

Manual tools provide deterministic analysis without allowing a model to choose
the next operation.

## Common CLI

```text
python main.py <phase> <sample> --tool <tool> [options]
```

Repeat `--tool` to run several tools:

```bash
python main.py static sample.exe --tool file --tool hash
```

Common options:

- `--output`: base output directory, default `output`.
- `--format json|text`: save results or print them.

With JSON output, results are merged into `analysis.json`.

## Static Tools

Available static modes:

| Mode | Purpose |
| --- | --- |
| `file` | Identify the file type. |
| `hash` | Calculate file hashes. |
| `metadata` | Extract file metadata. |
| `packer` | Detect possible packers. |
| `strings` | Extract and classify strings. |
| `pe` | Inspect PE headers, sections, imports, and related data. |
| `vt` | Query VirusTotal. |
| `full` | Run every registered static tool. |

Examples:

```bash
python main.py static sample.exe --tool full
python main.py static sample.exe --tool metadata --tool pe
```

`full` cannot be combined with another static mode.

Static analyzers are implemented in `tools/static/analyzers/` and registered in
`tools/static/manual.py`.

Some tools require external software:

- `file`
- `strings`
- `exiftool`
- `upx`

VirusTotal requires its configured API URL and key.

## Reversing Tools

Reversing tools use radare2 through `r2pipe`.

| Mode | Required option | Purpose |
| --- | --- | --- |
| `info` | None | Return binary information. |
| `imports` | None | List imported symbols. |
| `functions` | None | List analyzed functions. |
| `strings` | None | List radare2 strings. |
| `disasm` | `--function` | Return function metadata and instructions. |
| `xrefs` | `--function` | Find references to a function. |
| `string-xrefs` | `--value` | Find references to a string. |
| `import-xrefs` | `--value` | Find imports and their references. |
| `callers` | `--function` | Find functions calling a target. |
| `callees` | `--function` | Find functions called by a target. |
| `full` | None | Run `info`, `imports`, and `strings`. |

Examples:

```bash
python main.py reversing sample.exe --tool functions
python main.py reversing sample.exe --tool disasm --function fcn.401000
python main.py reversing sample.exe --tool disasm --function 0x401000
python main.py reversing sample.exe --tool xrefs --function sym.main
python main.py reversing sample.exe --tool string-xrefs --value "example.com"
python main.py reversing sample.exe --tool import-xrefs --value kernel32.dll
python main.py reversing sample.exe --tool import-xrefs --value VirtualAlloc
python main.py reversing sample.exe --tool callers --function fcn.401000
```

Function-oriented operations accept a radare2 function name or an address. When
an address belongs to an existing function, AIM resolves the containing
function.

`import-xrefs` accepts either a DLL name or an imported API name. Matching is
performed against both the import `name` and `libname` fields.

Reversing analyzers are implemented in `tools/reversing/analyzers/` and
registered in `tools/reversing/manual.py`.

## Dynamic Tools

Dynamic tools run inside the Windows victim VM and upload raw artifacts to the
REMnux receiver before host-side parsing.

| Tool | Purpose |
| --- | --- |
| `autoruns` | Capture autorun entries before and after execution. |
| `registry` | Export selected persistence-related registry keys before and after execution. |
| `procmon` | Capture Procmon activity and convert it to CSV. |
| `full` | Run every registered dynamic tool. |

Examples:

```bash
python main.py dynamic sample.exe --tool autoruns
python main.py dynamic sample.exe --tool registry --tool procmon
python main.py dynamic sample.exe --tool full --ai
```

Dynamic analyzers are implemented in `tools/dynamic/analyzers/` and registered
in `tools/dynamic/manual.py`.

See [Dynamic analysis setup](dynamic-analysis.md) for VM and agent setup.

## Adding a Manual Tool

1. Implement the analyzer in the owning `analyzers/` directory.
2. Register it in the phase's `manual.py`.
3. Add its mode and argument validation to the corresponding CLI parser.
4. Return useful data or raise an exception; the runner creates `ToolResult`.
5. Add a separate agent registration only if a model must call the operation.
