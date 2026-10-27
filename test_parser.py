from backend.parser import parse_incident

def test_extracts_request_status_duration_and_error():
    parsed=parse_incident({"method":"OTHER","logs":"2026-01-01T12:00:00Z POST /v1/items 422 response duration=1.5s\nValidation error: missing name"})
    assert parsed["method"]=="POST" and parsed["endpoint"]=="/v1/items"
    assert parsed["status_code"]==422 and parsed["duration_ms"]==1500
    assert "Validation error" in parsed["error_message"]
    assert parsed["parsed_timestamps"]

def test_malformed_log_is_nonfatal():
    assert parse_incident({"logs":"\x00 malformed ???"})["method"]=="OTHER"
