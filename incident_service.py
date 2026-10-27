from datetime import datetime, timezone
from uuid import uuid4
from typing import Any
from backend.database import get_connection, encode, decode
from backend.parser import parse_incident
from backend.classifier import classify_error
from backend.security import redact_data, redact_text
from backend.diagnosis import diagnose

JSON_FIELDS = {"request_metadata", "response_metadata", "headers"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row: Any) -> dict[str, Any]:
    data = dict(row)
    for key in JSON_FIELDS:
        data[key] = decode(data.get(key), {})
    return data


def create_incident(payload: dict[str, Any]) -> dict[str, Any]:
    safe = redact_data(payload)
    parsed = parse_incident(safe)
    classification = classify_error(parsed)
    incident_id, now = str(uuid4()), now_iso()
    data = {
        "id": incident_id, "title": redact_text(str(parsed.get("title", ""))),
        "api_name": redact_text(str(parsed.get("api_name", ""))),
        "method": parsed.get("method", "OTHER"), "endpoint": redact_text(str(parsed.get("endpoint", ""))),
        "status_code": parsed.get("status_code"), "error_message": redact_text(str(parsed.get("error_message", ""))),
        "request_metadata": encode(redact_data(parsed.get("request_metadata", {}))),
        "response_metadata": encode(redact_data(parsed.get("response_metadata", {}))),
        "headers": encode(redact_data(parsed.get("headers", {}))),
        "request_sample": redact_text(str(parsed.get("request_sample", ""))),
        "response_sample": redact_text(str(parsed.get("response_sample", ""))),
        "duration_ms": parsed.get("duration_ms"), "timestamp": str(parsed.get("timestamp") or ""),
        "logs": redact_text(str(parsed.get("logs", ""))), "category": classification["category"],
        "confidence": classification["confidence"], "status": "open", "created_at": now, "updated_at": now,
    }
    cols = ",".join(data.keys())
    placeholders = ",".join("?" for _ in data)
    with get_connection() as conn:
        conn.execute(f"INSERT INTO incidents ({cols}) VALUES ({placeholders})", tuple(data.values()))
    return get_incident(incident_id)


def get_incident(incident_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM incidents WHERE id=?", (incident_id,)).fetchone()
        if not row: return None
        result = _row_to_dict(row)
        result["diagnosis_history"] = [decode(r["result"], {}) for r in conn.execute("SELECT result FROM diagnoses WHERE incident_id=? ORDER BY id DESC", (incident_id,)).fetchall()]
        result["fix_attempts"] = [dict(r) for r in conn.execute("SELECT id,created_at,notes,outcome FROM fixes WHERE incident_id=? ORDER BY id DESC", (incident_id,)).fetchall()]
        result["test_scenarios"] = [dict(r) for r in conn.execute("SELECT id,created_at,name,expected_status,observed_status,input_sample,result,notes FROM scenarios WHERE incident_id=? ORDER BY id DESC", (incident_id,)).fetchall()]
    return result


def list_incidents(search: str = "", status: str = "", category: str = "", status_code: int | None = None, limit: int = 20, offset: int = 0) -> dict[str, Any]:
    where, args = [], []
    if search:
        term = f"%{search}%"
        where.append("(id LIKE ? OR api_name LIKE ? OR title LIKE ?)")
        args.extend([term, term, term])
    if status:
        where.append("status=?"); args.append(status)
    if category:
        where.append("category=?"); args.append(category)
    if status_code is not None:
        where.append("status_code=?"); args.append(status_code)
    clause = " WHERE " + " AND ".join(where) if where else ""
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM incidents" + clause, args).fetchone()[0]
        rows = conn.execute("SELECT id,title,api_name,method,endpoint,status_code,category,confidence,status,created_at,updated_at FROM incidents" + clause + " ORDER BY created_at DESC LIMIT ? OFFSET ?", (*args, limit, offset)).fetchall()
    return {"items": [dict(r) for r in rows], "total": total, "limit": limit, "offset": offset}


def change_status(incident_id: str, status: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        cur = conn.execute("UPDATE incidents SET status=?,updated_at=? WHERE id=?", (status, now_iso(), incident_id))
        if cur.rowcount == 0: return None
    return get_incident(incident_id)


def add_fix(incident_id: str, notes: str, outcome: str) -> dict[str, Any] | None:
    safe_notes = redact_text(notes)
    with get_connection() as conn:
        if not conn.execute("SELECT 1 FROM incidents WHERE id=?", (incident_id,)).fetchone(): return None
        conn.execute("INSERT INTO fixes(incident_id,created_at,notes,outcome) VALUES(?,?,?,?)", (incident_id, now_iso(), safe_notes, outcome))
        conn.execute("UPDATE incidents SET updated_at=? WHERE id=?", (now_iso(), incident_id))
    return get_incident(incident_id)


def add_scenario(incident_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    safe = redact_data(payload)
    with get_connection() as conn:
        if not conn.execute("SELECT 1 FROM incidents WHERE id=?", (incident_id,)).fetchone(): return None
        conn.execute("INSERT INTO scenarios(incident_id,created_at,name,expected_status,observed_status,input_sample,result,notes) VALUES(?,?,?,?,?,?,?,?)",
                     (incident_id, now_iso(), redact_text(safe["name"]), safe.get("expected_status"), safe.get("observed_status"), redact_text(safe.get("input_sample", "")), safe["result"], redact_text(safe.get("notes", ""))))
    return get_incident(incident_id)


def run_diagnosis(incident_id: str, use_ai: bool = True) -> dict[str, Any] | None:
    incident = get_incident(incident_id)
    if not incident: return None
    result = diagnose(incident, use_ai=use_ai)
    with get_connection() as conn:
        conn.execute("INSERT INTO diagnoses(incident_id,created_at,result) VALUES(?,?,?)", (incident_id, now_iso(), encode(redact_data(result))))
        conn.execute("UPDATE incidents SET category=?,confidence=?,updated_at=? WHERE id=?",
                     (result["classification"]["category"], result["classification"]["confidence"], now_iso(), incident_id))
    return redact_data(result)
