from typing import Any

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from config import (
    DYNAMIC_INFERENCE_RESULT_FILENAME,
    ENRICHMENT_FILENAME,
    REPORT_FILENAME,
    RESULT_FILENAME,
    REVERSING_AGENT_RESULT_FILENAME,
    STATIC_STRINGS_INFERENCE_RESULT_FILENAME,
)
from core.utils.crypto import sha256_file
from backend.analysis.service import AnalysisService
from backend.artifacts import (
    analysis_status,
    json_artifact,
    list_analyses,
    list_analysis_files,
    read_analysis_file,
    resolve_analysis,
    text_artifact,
)
from backend.storage import (
    WEB_ANALYSES_PATH,
    move_upload_to_sample_path,
    sample_path_for_status,
    save_upload_file,
    store_or_discard_duplicate_upload,
)
from backend.runner import DEFAULT_PIPELINE_NAME, PIPELINE_RUNNERS


service = AnalysisService(PIPELINE_RUNNERS)

app = FastAPI(title="AIM Web API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/analyses")
async def create_analysis(
    file: UploadFile = File(...),
    reanalyze: bool = Query(default=False),
    pipeline: str = Query(default=DEFAULT_PIPELINE_NAME),
) -> dict[str, Any]:
    pipeline_name = _validate_pipeline_name(pipeline)
    filename, sample_path = await save_upload_file(file)
    sample_sha256 = sha256_file(sample_path)

    if not reanalyze:
        try:
            status = resolve_analysis(service, sample_sha256)
            store_or_discard_duplicate_upload(sample_path, sample_sha256)
            return status
        except HTTPException as exc:
            if exc.status_code != 404:
                raise

    sample_path = move_upload_to_sample_path(sample_path, sample_sha256)
    
    output_base = WEB_ANALYSES_PATH / sample_sha256
    output_base.mkdir(parents=True, exist_ok=True)

    job = service.create(
        filename, 
        sample_path, 
        output_base, 
        pipeline_name,
    )
    result = job.to_status()

    return result


@app.get("/api/analyses")
def get_analyses() -> dict[str, Any]:
    result = list_analyses(service)

    return result


@app.get("/api/analyses/resolve/{identifier}")
def resolve_existing_analysis(identifier: str) -> dict[str, Any]:
    result = resolve_analysis(service, identifier)

    return result


@app.post("/api/analyses/{identifier}/reanalyze")
def reanalyze_existing_analysis(
    identifier: str,
    pipeline: str = Query(default=DEFAULT_PIPELINE_NAME),
) -> dict[str, Any]:
    pipeline_name = _validate_pipeline_name(pipeline)
    status = resolve_analysis(service, identifier)
    analysis_data = None
    if isinstance(status.get("analysis_id"), str):
        artifact = json_artifact(service, status["analysis_id"], RESULT_FILENAME)
        data = artifact.get("data")
        if isinstance(data, dict):
            analysis_data = data

    sample_path = sample_path_for_status(status, analysis_data)
    sample_sha256 = status.get("sample_sha256") or identifier
    filename = status.get("filename") or sample_path.name

    if not isinstance(sample_sha256, str) or not sample_sha256:
        raise HTTPException(
            status_code=400, 
            detail="Analysis has no sample hash",
        )

    output_base = WEB_ANALYSES_PATH / sample_sha256
    output_base.mkdir(parents=True, exist_ok=True)

    job = service.create(
        str(filename), 
        sample_path, 
        output_base, 
        pipeline_name,
    )
    result = job.to_status()

    return result


@app.get("/api/analyses/{analysis_id}/status")
def get_status(analysis_id: str) -> dict[str, Any]:
    return analysis_status(service, analysis_id)


@app.get("/api/analyses/{analysis_id}/analysis-json")
def get_analysis_json(analysis_id: str) -> dict[str, Any]:
    return json_artifact(service, analysis_id, RESULT_FILENAME)


@app.get("/api/analyses/{analysis_id}/files")
def get_analysis_files(analysis_id: str) -> dict[str, Any]:
    return list_analysis_files(service, analysis_id)


@app.get("/api/analyses/{analysis_id}/files/{file_path:path}")
def get_analysis_file(analysis_id: str, file_path: str) -> dict[str, Any]:
    return read_analysis_file(service, analysis_id, file_path)


@app.get("/api/analyses/{analysis_id}/static-inference")
def get_static_inference(analysis_id: str) -> dict[str, Any]:
    return json_artifact(
        service, 
        analysis_id, 
        STATIC_STRINGS_INFERENCE_RESULT_FILENAME,
    )


@app.get("/api/analyses/{analysis_id}/dynamic-inference")
def get_dynamic_inference(analysis_id: str) -> dict[str, Any]:
    return json_artifact(service, analysis_id, DYNAMIC_INFERENCE_RESULT_FILENAME)


@app.get("/api/analyses/{analysis_id}/enrichment")
def get_enrichment(analysis_id: str) -> dict[str, Any]:
    return text_artifact(service, analysis_id, ENRICHMENT_FILENAME)


@app.get("/api/analyses/{analysis_id}/reverse-agent")
def get_reverse_agent(analysis_id: str) -> dict[str, Any]:
    return json_artifact(service, analysis_id, REVERSING_AGENT_RESULT_FILENAME)


@app.get("/api/analyses/{analysis_id}/report")
def get_report(analysis_id: str) -> dict[str, Any]:
    return text_artifact(service, analysis_id, REPORT_FILENAME)


def _validate_pipeline_name(pipeline_name: str) -> str:
    if pipeline_name in PIPELINE_RUNNERS:
        return pipeline_name

    raise HTTPException(
        status_code=400,
        detail=f"Unknown pipeline: {pipeline_name}",
    )
