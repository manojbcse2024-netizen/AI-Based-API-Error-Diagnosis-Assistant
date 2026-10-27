import json
from backend.security import redact_text, redact_data, sanitize_json_text, csv_safe

def test_masks_auth_and_bearer():
    value=redact_text("Authorization: Bearer abc.def_123; api_key=secret-value")
    assert "abc.def_123" not in value and "secret-value" not in value
    assert "[REDACTED]" in value

def test_masks_nested_json_and_cookie():
    result=redact_data({"nested":{"password":"pw123"},"Cookie":"sid=xyz","safe":"ok"})
    assert result["nested"]["password"]=="[REDACTED]"
    assert result["Cookie"]=="[REDACTED]" and result["safe"]=="ok"

def test_masks_quoted_secret_with_spaces():
    value=redact_text('password="hello world with spaces"')
    assert "hello world with spaces" not in value and '[REDACTED]' in value

def test_sanitize_json_text_malformed_falls_back():
    out=sanitize_json_text('{"api_key":"abc"')
    assert "abc" not in out

def test_csv_formula_injection():
    assert csv_safe("=HYPERLINK('x')").startswith("'=")
