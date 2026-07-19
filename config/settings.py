import os
from pathlib import Path

from dotenv import load_dotenv


# Paths
ROOT_PATH = Path(__file__).resolve().parent.parent

CONFIG_PATH = ROOT_PATH / "config"
CORE_PATH = ROOT_PATH / "core"
OUTPUT_PATH = ROOT_PATH / "output"
SHARED_PATH = ROOT_PATH / "shared"

DYNAMIC_EXECUTION_PATH = SHARED_PATH / "execution"
DYNAMIC_ARTIFACTS_PATH = SHARED_PATH / "artifacts"

ORCHESTRATOR_PATH = CORE_PATH / "orchestrator"
TOOLS_PATH = CORE_PATH / "tools"
AI_PATH = CORE_PATH / "ai"

STATIC_TOOLS_PATH = TOOLS_PATH / "static"
REVERSING_TOOLS_PATH = TOOLS_PATH / "reversing"
REVERSING_AGENT_TOOLS_PATH = REVERSING_TOOLS_PATH / "agent_tools.json"

MODEL_PROFILES_PATH = AI_PATH / "model_profiles.yaml"

VBOXMANAGE_PATH = "/mnt/c/Program Files/Oracle/VirtualBox/VBoxManage.exe"
VICTIM_WORKING_PATH = "C:\\AIM"

# Filenames
RESULT_FILENAME = "analysis.json"
STATIC_STRINGS_INFERENCE_RESULT_FILENAME = "static_strings_inference.json"
DYNAMIC_INFERENCE_RESULT_FILENAME = "dynamic_inference.json"
DYNAMIC_JOB_FILENAME = "job.json"
REVERSING_AGENT_RESULT_FILENAME = "reversing_agent.json"
REPORT_FILENAME = "report.md"
ENRICHMENT_FILENAME = "enrichment.md"

# Folders
SHARED_FOLDER = "shared"


# Load .env file
load_dotenv()


def get_env(name: str) -> str:
    value = os.getenv(name)

    if value is None:
        raise RuntimeError(f"Environment variable '{name}' is required")
    
    return value






