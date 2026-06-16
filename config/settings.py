import os
from pathlib import Path

from dotenv import load_dotenv


# Load .env file
load_dotenv()


def get_env(name: str) -> str:
    value = os.getenv(name)
    if value is None:
        raise RuntimeError(f"Environment variable '{name}' is required")
    return value


# Paths
ROOT_PATH = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_PATH / "config"
ORCHESTRATOR_PATH = ROOT_PATH / "orchestrator"
OUTPUT_PATH = ROOT_PATH / "output"
AI_PATH = ROOT_PATH / "ai"
MODEL_PROFILES_PATH = AI_PATH / "model_profiles.yaml"

TOOLS_PATH = ROOT_PATH / "tools"
STATIC_TOOLS_PATH = TOOLS_PATH / "static"
STATIC_AGENT_TOOLS_PATH = STATIC_TOOLS_PATH / "tools.json"


# Filenames
RESULT_FILENAME = "analysis.json"
STATIC_AGENT_RESULT_FILENAME = "static_agent_steps.json"
THREAT_ACTOR_MESSAGES_FILENAME = "threat_actor_messages.json"
REPORT_FILENAME = "report.md"
ENRICHMENT_FILENAME = "enrichment.md"


