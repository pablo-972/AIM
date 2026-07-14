from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend.analysis import AnalysisStore
from backend.artifacts import (
    analysis_status,
    json_artifact,
    list_analyses,
    list_analysis_files,
    read_analysis_file,
    text_artifact,
)
from backend.files import WEB_ANALYSES_PATH, save_upload_file
from config import (
    DYNAMIC_INFERENCE_RESULT_FILENAME,
    ENRICHMENT_FILENAME,
    REPORT_FILENAME,
    RESULT_FILENAME,
    REVERSING_AGENT_RESULT_FILENAME,
    STATIC_STRINGS_INFERENCE_RESULT_FILENAME,
)


store = AnalysisStore()
app = FastAPI(title="AIM Web API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/analyses")
async def create_analysis(file: UploadFile = File(...)) -> dict[str, Any]:
    analysis_id = uuid4().hex
    filename, sample_path = await save_upload_file(file, analysis_id)

    output_base = WEB_ANALYSES_PATH / analysis_id
    output_base.mkdir(parents=True, exist_ok=True)

    job = store.create(filename, sample_path, output_base)
    return job.to_status()


@app.get("/api/analyses")
def get_analyses() -> dict[str, Any]:
    return list_analyses(store)


@app.get("/api/analyses/{analysis_id}/status")
def get_status(analysis_id: str) -> dict[str, Any]:
    return analysis_status(store, analysis_id)


@app.get("/api/analyses/{analysis_id}/analysis-json")
def get_analysis_json(analysis_id: str) -> dict[str, Any]:
    return json_artifact(store, analysis_id, RESULT_FILENAME)


@app.get("/api/analyses/{analysis_id}/files")
def get_analysis_files(analysis_id: str) -> dict[str, Any]:
    return list_analysis_files(store, analysis_id)


@app.get("/api/analyses/{analysis_id}/files/{file_path:path}")
def get_analysis_file(analysis_id: str, file_path: str) -> dict[str, Any]:
    return read_analysis_file(store, analysis_id, file_path)


@app.get("/api/analyses/{analysis_id}/static-inference")
def get_static_inference(analysis_id: str) -> dict[str, Any]:
    return json_artifact(store, analysis_id, STATIC_STRINGS_INFERENCE_RESULT_FILENAME)


@app.get("/api/analyses/{analysis_id}/dynamic-inference")
def get_dynamic_inference(analysis_id: str) -> dict[str, Any]:
    return json_artifact(store, analysis_id, DYNAMIC_INFERENCE_RESULT_FILENAME)


@app.get("/api/analyses/{analysis_id}/enrichment")
def get_enrichment(analysis_id: str) -> dict[str, Any]:
    return text_artifact(store, analysis_id, ENRICHMENT_FILENAME)


@app.get("/api/analyses/{analysis_id}/reverse-agent")
def get_reverse_agent(analysis_id: str) -> dict[str, Any]:
    return json_artifact(store, analysis_id, REVERSING_AGENT_RESULT_FILENAME)


@app.get("/api/analyses/{analysis_id}/report")
def get_report(analysis_id: str) -> dict[str, Any]:
    return text_artifact(store, analysis_id, REPORT_FILENAME)
