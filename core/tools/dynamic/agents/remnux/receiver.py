from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Request


API_HOST = "0.0.0.0"
API_PORT = 8080

RESULTS_PATH = Path("/home/remnux/AIM")

app = FastAPI(title="AIM REMnux Dynamic Receiver")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/jobs/{sha256}/result")
async def receive_result(sha256: str, request: Request) -> dict[str, Any]:
    await request.body()
    return {
        "status": "ignored",
        "sha256": sha256,
    }


@app.post("/jobs/{sha256}/log")
async def receive_log(sha256: str, request: Request) -> dict[str, Any]:
    await request.body()
    return {
        "status": "ignored",
        "sha256": sha256,
    }


@app.post("/jobs/{sha256}/tools/{tool_name}/result")
async def receive_tool_result(
    sha256: str,
    tool_name: str,
    request: Request,
) -> dict[str, Any]:
    await request.body()
    return {
        "status": "ignored",
        "sha256": sha256,
        "tool": tool_name,
    }


@app.post("/jobs/{sha256}/tools/{tool_name}/artifacts/{artifact_name:path}")
async def receive_tool_artifact(
    sha256: str,
    tool_name: str,
    artifact_name: str,
    request: Request,
) -> dict[str, Any]:
    content = await request.body()
    path = _artifact_path(tool_name, artifact_name)
    _write_bytes(path, content)

    return {
        "status": "ok",
        "sha256": sha256,
        "tool": tool_name,
        "artifact": artifact_name,
        "path": str(path),
        "size": len(content),
    }


@app.get("/jobs/{sha256}/result")
def get_result(sha256: str) -> dict[str, Any]:
    return {
        "status": "artifact_only",
        "sha256": sha256,
        "artifacts_path": str(RESULTS_PATH),
    }


def _write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _artifact_path(tool_name: str, artifact_name: str) -> Path:
    clean_parts = []
    for part in Path(artifact_name).parts:
        safe = _safe_name(part)
        if safe:
            clean_parts.append(safe)
    if not clean_parts:
        clean_parts = ["artifact.bin"]
    return RESULTS_PATH / _safe_name(tool_name) / Path(*clean_parts)


def _safe_name(value: str) -> str:
    safe = []
    for char in str(value):
        if char.isalnum() or char in {".", "_", "-"}:
            safe.append(char)
        else:
            safe.append("_")
    return "".join(safe).strip("._") or "item"


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=API_HOST,
        port=API_PORT,
    )
