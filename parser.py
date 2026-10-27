import re
from typing import Any
from backend.security import redact_text, redact_data

METHOD_RE = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(\S+)", re.I)
STATUS_RE = re.compile(r"(?i)(?:status(?:_code)?|http)[\s:=]+([1-5]\d\d)\b|\b([1-5]\d\d)\s+(?:error|response|returned|status)\b")
DURATION_RE = re.compile(r"(?i)(?:duration|latency|elapsed)[\s:=]+([0-9]+(?:\.[0-9]+)?)\s*(ms|s|seconds?)?\b")
TIME_RE = re.compile(r"\b\d{4}-\d\d-\d\d[T ][\d:.+-]+Z?\b")


def parse_incident(data: dict[str, Any]) -> dict[str, Any]:
    """Extract useful clues without treating malformed log text as fatal."""
    result = dict(data)
    logs = str(data.get("logs", "") or "")
    endpoint = str(data.get("endpoint", "") or "")
    method = str(data.get("method", "") or "").upper()
    status = data.get("status_code")
    duration = data.get("duration_ms")
    match = METHOD_RE.search(logs)
    if match:
        if not method or method == "OTHER":
            method = match.group(1).upper()
        if not endpoint:
            endpoint = match.group(2)
    status_match = STATUS_RE.search(logs)
    if status is None and status_match:
        status = int(status_match.group(1) or status_match.group(2))
    duration_match = DURATION_RE.search(logs)
    if duration is None and duration_match:
        duration = float(duration_match.group(1)) * (1000 if (duration_match.group(2) or "ms").lower().startswith("s") else 1)
    timestamps = TIME_RE.findall(logs)
    error = str(data.get("error_message", "") or "")
    if not error:
        for line in logs.splitlines():
            if re.search(r"(?i)\b(error|exception|failed|failure|traceback)\b", line):
                error = line[:2000]
                break
    return {
        **result, "method": method or "OTHER", "endpoint": endpoint,
        "status_code": status, "duration_ms": duration,
        "error_message": redact_text(error), "logs": redact_text(logs),
        "headers": redact_data(data.get("headers") or {}),
        "parsed_timestamps": timestamps,
    }
