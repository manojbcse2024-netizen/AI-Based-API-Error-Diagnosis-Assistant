import os
import tempfile
from pathlib import Path

_tmp = tempfile.TemporaryDirectory(prefix="api-diagnosis-tests-")
os.environ["DATABASE_PATH"] = str(Path(_tmp.name) / "test.db")
os.environ.pop("LLM_API_KEY", None)

import pytest
from fastapi.testclient import TestClient
from backend.database import init_db, get_connection
from backend.main import app

@pytest.fixture(autouse=True)
def fresh_database():
    init_db()
    with get_connection() as conn:
        for table in ("diagnoses", "fixes", "scenarios", "documents", "incidents"):
            conn.execute(f"DELETE FROM {table}")
    yield

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
