from typing import Any

CATEGORY = {
    "authentication": "Authentication",
    "authorization": "Authorization",
    "validation": "Validation",
    "rate_limit": "Rate limit",
    "timeout": "Timeout",
    "server": "Server error",
    "unknown": "Unknown / other",
}


def classify_error(incident: dict[str, Any]) -> dict[str, Any]:
    status = incident.get("status_code")
    text = " ".join(str(incident.get(k, "")) for k in ("error_message", "logs")).lower()
    evidence: list[str] = []
    category, confidence = "unknown", 0.25
    if status == 401 or any(x in text for x in ("invalid token", "missing token", "authentication required", "unauthenticated")):
        category, confidence = "authentication", 0.92 if status == 401 else 0.72
        if status == 401: evidence.append("HTTP status 401")
    elif status == 403 or any(x in text for x in ("forbidden", "insufficient scope", "permission denied", "not authorized")):
        category, confidence = "authorization", 0.92 if status == 403 else 0.72
        if status == 403: evidence.append("HTTP status 403")
    elif status in (400, 422) or any(x in text for x in ("validation error", "invalid field", "missing required", "malformed request")):
        category, confidence = "validation", 0.9 if status in (400, 422) else 0.7
        if status in (400, 422): evidence.append(f"HTTP status {status}")
    elif status == 429 or "rate limit" in text or "too many requests" in text:
        category, confidence = "rate_limit", 0.95 if status == 429 else 0.76
        if status == 429: evidence.append("HTTP status 429")
    elif status in (408, 504) or any(x in text for x in ("timed out", "timeout", "deadline exceeded")):
        category, confidence = "timeout", 0.9 if status in (408, 504) else 0.72
        if status in (408, 504): evidence.append(f"HTTP status {status}")
    elif (isinstance(status, int) and 500 <= status <= 599) or any(x in text for x in ("internal server error", "service unavailable", "upstream failure")):
        category, confidence = "server", 0.9 if isinstance(status, int) and status >= 500 else 0.7
        if isinstance(status, int) and status >= 500: evidence.append(f"HTTP status {status}")
    if incident.get("error_message"):
        evidence.append("Error message supplied in incident data")
    if incident.get("duration_ms") is not None:
        evidence.append(f"Request duration recorded: {incident['duration_ms']} ms")
    evidence = list(dict.fromkeys(evidence))
    return {"key": category, "category": CATEGORY[category], "confidence": confidence,
            "uncertain": confidence < 0.8, "evidence": evidence,
            "explanation": _explanation(category, status)}


def _explanation(category: str, status: int | None) -> str:
    return {
        "authentication": "The supplied status or error text points to missing, invalid, or expired identity credentials. This does not establish which credential is at fault.",
        "authorization": "Evidence points to a permission, role, or scope restriction after the request reached the service.",
        "validation": "Evidence indicates the service rejected the request shape or one or more field values.",
        "rate_limit": "Evidence indicates a request quota or rate limit was reached.",
        "timeout": "Evidence indicates a request deadline or timeout condition; the failure may occur at the client, gateway, or upstream service.",
        "server": "Evidence indicates a server-side or upstream error. Client input is not necessarily the cause.",
        "unknown": "Available evidence is insufficient for a reliable category. Treat this as a tentative classification.",
    }[category]
