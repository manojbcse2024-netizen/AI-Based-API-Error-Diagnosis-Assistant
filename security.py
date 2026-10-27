"""Best-effort secret masking. Always review sanitized content before analysis."""
import json
import re
from typing import Any

REDACTED = "[REDACTED]"
SENSITIVE_KEY = re.compile(r"(?:authorization|proxy-authorization|api[_-]?key|access[_-]?token|refresh[_-]?token|id[_-]?token|token|password|passwd|secret|client[_-]?secret|cookie|set-cookie|session(?:id|_id)?|private[_-]?key|credential)", re.I)
BEARER = re.compile(r"(?i)\b(Bearer\s+)[A-Za-z0-9._~+\-/]+=*")
BASIC = re.compile(r"(?i)\b(Basic\s+)[A-Za-z0-9+/]+=*")
KEY_PATTERN = r"(?:authorization|proxy-authorization|api[_-]?key|access[_-]?token|refresh[_-]?token|id[_-]?token|token|password|passwd|secret|client[_-]?secret|cookie|set-cookie|session(?:id|_id)?|private[_-]?key|credential)"
QUOTED_ASSIGNMENT = re.compile(r'''(?is)(\b''' + KEY_PATTERN + r'''\b\s*["']?\s*[:=]\s*)(["'])(.*?)\2''')
ASSIGNMENT = re.compile(r'''(?i)(\b''' + KEY_PATTERN + r'''\b\s*["']?\s*[:=]\s*["']?)([^\s,"';&}]+)''')
QUERY_SECRET = re.compile(r"(?i)([?&](?:api[_-]?key|access[_-]?token|token|password|secret|client[_-]?secret|session(?:id|_id)?|key)=)[^&#\s]+")


def redact_text(value: str) -> str:
    if not isinstance(value, str):
        value = str(value)
    value = BEARER.sub(lambda m: m.group(1) + REDACTED, value)
    value = BASIC.sub(lambda m: m.group(1) + REDACTED, value)
    value = QUERY_SECRET.sub(lambda m: m.group(1) + REDACTED, value)
    value = QUOTED_ASSIGNMENT.sub(lambda m: m.group(1) + m.group(2) + REDACTED + m.group(2), value)
    value = ASSIGNMENT.sub(lambda m: m.group(1) + REDACTED, value)
    return value


def redact_data(value: Any) -> Any:
    """Recursively mask sensitive mapping values and redact strings everywhere."""
    if isinstance(value, dict):
        return {str(k): (REDACTED if SENSITIVE_KEY.search(str(k)) else redact_data(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_data(v) for v in value]
    if isinstance(value, tuple):
        return [redact_data(v) for v in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def sanitize_headers(headers: Any) -> dict[str, Any]:
    if not isinstance(headers, dict):
        return {}
    return redact_data(headers)


def sanitize_json_text(raw: str) -> str:
    """Parse and structurally sanitize JSON when possible; safely fall back to text masking."""
    try:
        parsed = json.loads(raw)
        return json.dumps(redact_data(parsed), ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        return redact_text(raw)


def csv_safe(value: Any) -> str:
    text = redact_text(str(value if value is not None else ""))
    if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + text
    return text
