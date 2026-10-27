"""Seed a synthetic example incident for local evaluation: python seed_demo.py"""
from backend.database import init_db
from backend.incident_service import create_incident

init_db()
incident = create_incident({
    "title": "Inventory create request rejected",
    "api_name": "Example Inventory API",
    "method": "POST",
    "endpoint": "/v1/items",
    "status_code": 422,
    "error_message": "Validation error: required field 'quantity' is missing",
    "headers": {"Content-Type": "application/json", "X-Request-ID": "demo-req-001"},
    "request_sample": '{"name":"desk lamp"}',
    "response_sample": '{"detail":"quantity is required"}',
    "duration_ms": 84,
    "timestamp": "2026-01-15T12:00:00Z",
    "logs": "2026-01-15T12:00:00Z POST /v1/items 422 response duration=84ms",
})
print(f"Created synthetic demo incident: {incident['id']}")
