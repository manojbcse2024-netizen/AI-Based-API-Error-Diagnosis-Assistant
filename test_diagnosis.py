from backend.database import init_db
from backend.diagnosis import diagnose
from backend.retrieval import index_document

def test_rule_based_fallback_without_key(monkeypatch):
    monkeypatch.setattr("backend.diagnosis.LLM_API_KEY", "")
    result=diagnose({"api_name":"sample","status_code":401,"method":"GET","endpoint":"/v1/me"})
    assert result["mode"]=="rules"
    assert result["classification"]["key"]=="authentication"
    assert result["observed_facts"] and result["troubleshooting_steps"]
    assert "not configured" in result["provider_status"]

def test_retrieval_returns_source_reference():
    index_document("guide.md",b"## Authentication\nA 401 response means authentication is missing or invalid.\n")
    result=diagnose({"api_name":"sample","status_code":401,"error_message":"authentication missing"},use_ai=False)
    assert result["documentation_references"]
    assert result["documentation_references"][0]["filename"]=="guide.md"
    assert result["documentation_references"][0]["reference"].startswith("lines")
