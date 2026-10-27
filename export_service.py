import csv
import io
from typing import Any
from backend.security import redact_data, redact_text, csv_safe


def report_data(incident: dict[str, Any]) -> dict[str, Any]:
    latest = (incident.get("diagnosis_history") or [None])[0] or {}
    return redact_data({
        "incident_id": incident.get("id"), "title": incident.get("title"), "api_name": incident.get("api_name"),
        "endpoint_pattern": incident.get("endpoint"), "http_method": incident.get("method"), "status_code": incident.get("status_code"),
        "error_classification": incident.get("category"), "sanitized_summary": latest.get("summary", incident.get("error_message", "")),
        "observed_facts": latest.get("observed_facts", []), "likely_causes": latest.get("likely_causes", []),
        "uncertainty": latest.get("uncertainty", "Diagnosis not yet run."),
        "recommended_steps": latest.get("troubleshooting_steps", []),
        "source_references": latest.get("documentation_references", []),
        "fix_attempts": incident.get("fix_attempts", []), "status": incident.get("status"),
        "created_at": incident.get("created_at"), "updated_at": incident.get("updated_at"),
    })


def export_json(incident: dict[str, Any]) -> str:
    import json
    return json.dumps(report_data(incident), indent=2, ensure_ascii=False)


def export_csv(incident: dict[str, Any]) -> str:
    report = report_data(incident)
    fields = list(report.keys())
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, quoting=csv.QUOTE_ALL)
    writer.writeheader()
    row = {}
    for field, value in report.items():
        if isinstance(value, (dict, list)):
            import json
            value = json.dumps(value, ensure_ascii=False)
        row[field] = csv_safe(value)
    writer.writerow(row)
    return output.getvalue()
