import csv, io

def sample_payload():
    return {"title":"Sample outage","api_name":"inventory","method":"POST","endpoint":"/v1/items","status_code":401,"error_message":"Authorization: Bearer supersecret","headers":{"Authorization":"Bearer supersecret","X-Request-ID":"req-1"},"request_sample":"{\"api_key\":\"secret123\"}","logs":"POST /v1/items 401 response duration=50ms"}

def test_health_and_incident_crud_sanitization(client):
    assert client.get("/health").json()["status"]=="ok"
    created=client.post("/incidents",json=sample_payload())
    assert created.status_code==201
    iid=created.json()["id"]
    detail=client.get(f"/incidents/{iid}").json()
    assert detail["category"]=="Authentication"
    assert "supersecret" not in str(detail) and "secret123" not in str(detail)
    assert client.get("/incidents",params={"search":"inventory"}).json()["total"]==1

def test_fix_status_scenario_diagnosis_and_exports(client):
    iid=client.post("/incidents",json=sample_payload()).json()["id"]
    assert client.post(f"/incidents/{iid}/diagnose",params={"use_ai":"false"}).status_code==200
    assert client.patch(f"/incidents/{iid}/status",json={"status":"investigating"}).json()["status"]=="investigating"
    fix=client.post(f"/incidents/{iid}/fix-attempts",json={"notes":"Updated safe config; token=not-real-secret","outcome":"pending"})
    assert fix.status_code==201 and "not-real-secret" not in str(fix.json())
    scenario=client.post(f"/incidents/{iid}/test-scenarios",json={"name":"mock regression","expected_status":200,"observed_status":401,"input_sample":"password=plain","result":"fail"})
    assert scenario.status_code==201 and "plain" not in str(scenario.json())
    j=client.get(f"/incidents/{iid}/export?format=json")
    assert j.status_code==200 and "supersecret" not in j.text
    c=client.get(f"/incidents/{iid}/export?format=csv")
    assert c.status_code==200 and "supersecret" not in c.text
    assert next(csv.reader(io.StringIO(c.text)))

def test_invalid_input_and_missing_incident(client):
    assert client.post("/incidents",json={"title":"x"}).status_code==422
    assert client.get("/incidents/not-found").status_code==404

def test_document_upload_validation(client):
    ok=client.post("/documents/upload",files={"file":("api.md",b"# API\nReturns 429 on rate limit.","text/markdown")})
    assert ok.status_code==201 and ok.json()["passages_indexed"]==1
    bad=client.post("/documents/upload",files={"file":("x.exe",b"no","application/octet-stream")})
    assert bad.status_code==400

def test_csv_formula_injection_export(client):
    payload=sample_payload(); payload["title"]="=1+1"
    iid=client.post("/incidents",json=payload).json()["id"]
    out=client.get(f"/incidents/{iid}/export?format=csv").text
    assert "'=1+1" in out
