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
| `AIM_DYNAMIC_VICTIM_VM` | Dynamic analysis is used | VirtualBox name of the Windows victim VM |
| `AIM_DYNAMIC_VICTIM_SNAPSHOT` | Dynamic analysis is used | Snapshot restored before execution |
| `AIM_DYNAMIC_VICTIM_SHARED_PATH` | Dynamic analysis is used | Windows path to the shared execution folder |
| `AIM_DYNAMIC_ANALYSIS_VM` | Dynamic analysis is used | VirtualBox name of the REMnux analysis VM |
| `AIM_DYNAMIC_ANALYSIS_SHARED_MOUNT_POINT` | Dynamic analysis is used | REMnux mount point for received artifacts |
| `AIM_DYNAMIC_ANALYSIS_BASE_URL` | Dynamic analysis is used | URL of the REMnux receiver |
| `AIM_DYNAMIC_ANALYSIS_TIMEOUT` | Dynamic analysis is used | Timeout used for receiver communication |
| `OLLAMA_BASE_URL` | Local AI profiles are used | Ollama endpoint |
| `OLLAMA_PRELOAD_MODELS` | Docker Ollama is used | Models preloaded by the Ollama container |
| `OPENAI_API_KEY` | OpenAI profiles are used | OpenAI API key |
| `OPENAI_BASE_URL` | OpenAI profiles are used | OpenAI-compatible base URL |
| `GEMINI_API_KEY` | Gemini profiles are used | Gemini API key |
| `GEMINI_BASE_URL` | Gemini profiles are used | Gemini OpenAI-compatible base URL |

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
- Use `host.docker.internal` for Docker-to-host access when supported by your
  environment.
- Configure only the providers you actually use.


