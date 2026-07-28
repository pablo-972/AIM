# Configuration

AIM reads runtime configuration from environment variables. Start by copying the
template file:

```bash
cp .env.example .env
```

The `.env` file defines external services, model providers, VirtualBox
connectivity, dynamic VM names, and dynamic lab endpoints. Keep secrets such as
API keys out of version control.

## Important Variables

| Variable | Required When | Purpose |
| --- | --- | --- |
| `VT_API_KEY` | VirusTotal static tool is used | VirusTotal API key |
| `VT_API_BASE_URL` | VirusTotal static tool is used | VirusTotal API base URL |
| `AIM_VBOXMANAGE_API_HOST` | Dynamic analysis is used | Hostname for the VirtualBox Manager API |
| `AIM_VBOXMANAGE_API_PORT` | Dynamic analysis is used | Port for the VirtualBox Manager API |
| `AIM_VBOXMANAGE_PATH` | Optional for dynamic analysis | Override path to `VBoxManage.exe` for the environment running the VirtualBox Manager API |
| `AIM_DYNAMIC_VICTIM_VM` | Dynamic analysis is used | VirtualBox name of the Windows victim VM |
| `AIM_DYNAMIC_VICTIM_SNAPSHOT` | Dynamic analysis is used | Snapshot restored before execution |
| `AIM_DYNAMIC_VICTIM_SHARED_PATH` | Dynamic analysis is used | Windows path to the shared execution folder |
| `AIM_DYNAMIC_ANALYSIS_VM` | Dynamic analysis is used | VirtualBox name of the REMnux analysis VM |
| `AIM_DYNAMIC_ANALYSIS_SHARED_MOUNT_POINT` | Dynamic analysis is used | REMnux mount point for received artifacts |
| `AIM_DYNAMIC_ANALYSIS_BASE_URL` | Dynamic analysis is used | URL of the REMnux receiver |
| `AIM_DYNAMIC_ANALYSIS_TIMEOUT` | Dynamic analysis is used | Timeout used for receiver communication |
| `OLLAMA_BASE_URL` | Local AI profiles are used | Ollama endpoint |
| `OLLAMA_PRELOAD_MODELS` | Docker Ollama is used | Models preloaded by the Ollama container |
| `LOCAL_STATIC_MODEL` | Local static AI profile is used | Ollama model for static inference |
| `LOCAL_STATIC_NUM_CTX` | Local static AI profile is used | Ollama context window for static inference |
| `LOCAL_DYNAMIC_MODEL` | Local dynamic AI profile is used | Ollama model for dynamic inference |
| `LOCAL_DYNAMIC_NUM_CTX` | Local dynamic AI profile is used | Ollama context window for dynamic inference |
| `LOCAL_ENRICHMENT_MODEL` | Local enrichment profile is used | Ollama model for enrichment |
| `LOCAL_ENRICHMENT_NUM_CTX` | Local enrichment profile is used | Ollama context window for enrichment |
| `LOCAL_REVERSING_MODEL` | Local reversing agent profile is used | Ollama model for the reversing agent |
| `LOCAL_REVERSING_NUM_CTX` | Local reversing agent profile is used | Ollama context window for the reversing agent |
| `LOCAL_REPORT_MODEL` | Local report profile is used | Ollama model for report generation |
| `LOCAL_REPORT_NUM_CTX` | Local report profile is used | Ollama context window for report generation |
| `OPENAI_API_KEY` | OpenAI profiles are used | OpenAI API key |
| `OPENAI_BASE_URL` | OpenAI profiles are used | OpenAI-compatible base URL |
| `GEMINI_API_KEY` | Gemini profiles are used | Gemini API key |
| `GEMINI_BASE_URL` | Gemini profiles are used | Gemini native API base URL |

Local model variables are task-specific:

```text
LOCAL_STATIC_MODEL
LOCAL_DYNAMIC_MODEL
LOCAL_ENRICHMENT_MODEL
LOCAL_REVERSING_MODEL
LOCAL_REPORT_MODEL
```

Local context variables use Ollama's `num_ctx` option:

```text
LOCAL_STATIC_NUM_CTX
LOCAL_DYNAMIC_NUM_CTX
LOCAL_ENRICHMENT_NUM_CTX
LOCAL_REVERSING_NUM_CTX
LOCAL_REPORT_NUM_CTX
```

Cloud model variables are task-specific:

```text
OPENAI_STATIC_MODEL
OPENAI_DYNAMIC_MODEL
OPENAI_ENRICHMENT_MODEL
OPENAI_REVERSING_MODEL
OPENAI_REPORT_MODEL
GEMINI_STATIC_MODEL
GEMINI_DYNAMIC_MODEL
GEMINI_ENRICHMENT_MODEL
GEMINI_REVERSING_MODEL
GEMINI_REPORT_MODEL
```

## Recommendations

- Keep `.env.example` as a template and edit only `.env`.
- Use exact VirtualBox VM and snapshot names.
- AIM autodetects the `VBoxManage` path for Windows PowerShell, WSL, and Linux.
  Set `AIM_VBOXMANAGE_PATH` only if VirtualBox is installed somewhere else.
- Use `host.docker.internal` for Docker-to-host access when supported by your
  environment.
- Configure only the providers you actually use.
