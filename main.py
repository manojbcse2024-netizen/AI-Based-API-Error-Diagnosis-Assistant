from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from backend.database import init_db
from backend.schemas import IncidentCreate, IncidentStatusUpdate, FixAttemptCreate, ScenarioCreate
from backend.incident_service import create_incident, get_incident, list_incidents, change_status, add_fix, add_scenario, run_diagnosis
from backend.retrieval import index_document, list_documents, SUPPORTED_EXTENSIONS
from backend.export_service import export_json, export_csv
from backend.config import MAX_UPLOAD_BYTES


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="AI-Based API Error Diagnosis Assistant", version="1.0.0",
              description="Sanitized, evidence-led API incident analysis. Review redacted data before use.", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
                   allow_credentials=False, allow_methods=["GET", "POST", "PATCH"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "api-error-diagnosis", "database": "sqlite"}


@app.post("/incidents", status_code=201)
def post_incident(payload: IncidentCreate):
    try:
        return create_incident(payload.model_dump(mode="json"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Incident could not be saved safely.") from exc


@app.get("/incidents")
def get_incidents(search: str = "", status: str = "", category: str = "", status_code: int | None = None,
                  limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
    return list_incidents(search, status, category, status_code, limit, offset)


@app.get("/incidents/{incident_id}")
def incident_detail(incident_id: str):
    result = get_incident(incident_id)
    if not result:
        raise HTTPException(status_code=404, detail="Incident not found")
    return result


@app.post("/incidents/{incident_id}/diagnose")
def diagnose_incident(incident_id: str, use_ai: bool = True):
    result = run_diagnosis(incident_id, use_ai=use_ai)
    if result is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return result


@app.patch("/incidents/{incident_id}/status")
def patch_status(incident_id: str, payload: IncidentStatusUpdate):
    result = change_status(incident_id, payload.status)
    if not result:
        raise HTTPException(status_code=404, detail="Incident not found")
    return result


@app.post("/incidents/{incident_id}/fix-attempts", status_code=201)
def post_fix(incident_id: str, payload: FixAttemptCreate):
    result = add_fix(incident_id, payload.notes, payload.outcome)
    if not result:
        raise HTTPException(status_code=404, detail="Incident not found")
    return result


@app.post("/documents/upload", status_code=201)
async def upload_document(file: UploadFile = File(...)):
    filename = file.filename or "upload.txt"
    if Path(filename).suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Allowed types: TXT, Markdown, JSON, YAML")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_UPLOAD_BYTES} byte limit")
    try:
        return index_document(Path(filename).name, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/documents")
def documents():
    return {"items": list_documents()}


@app.post("/incidents/{incident_id}/test-scenarios", status_code=201)
def post_scenario(incident_id: str, payload: ScenarioCreate):
    result = add_scenario(incident_id, payload.model_dump())
    if not result:
        raise HTTPException(status_code=404, detail="Incident not found")
    return result


@app.get("/incidents/{incident_id}/export")
def export_incident(incident_id: str, format: str = Query("json", pattern="^(json|csv)$")):
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if format == "csv":
        return Response(export_csv(incident), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="incident-{incident_id}.csv"'})
    return Response(export_json(incident), media_type="application/json; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="incident-{incident_id}.json"'})
