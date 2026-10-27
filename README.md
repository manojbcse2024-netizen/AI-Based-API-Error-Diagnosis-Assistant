# AI-Based API Error Diagnosis Assistant

A local developer tool for organizing sanitized API incidents, classifying common errors, retrieving approved local API documentation, and generating evidence-led troubleshooting suggestions. It uses FastAPI, Streamlit, Pydantic, and SQLite. Deterministic diagnosis works without an external AI key; optional OpenAI-compatible AI assistance can be configured by environment variables.

> **Security warning:** Never share API keys, access tokens, passwords, cookies, private keys, or other secrets. Secret detection is best-effort, not perfect. Review all sanitized data before submitting it. This application does not include user authentication or database encryption; use it only on a trusted local machine or a suitably protected private network.

## What is implemented

- Dashboard metrics and incident/category/status-code visualizations, recent incident list, incident search and category/status filters.
- Incident intake with input validation, best-effort secret masking, preview-before-submit workflow, metadata, headers, request/response samples, duration, timestamp, and logs.
- Log clue parsing and deterministic classification for authentication, authorization, validation, rate limits, timeouts, server failures, and unknown cases. Confidence and evidence are shown.
- Structured rule-based diagnosis with observed facts, hypotheses, alternatives, uncertainty, ordered steps, safe mock/non-production tests, and local documentation citations. Optional LLM response is constrained to structured suggestions and has safe fallback.
- TXT, Markdown, JSON, and YAML document upload and local searchable passage indexing; citations include filename and line range. Documents are never executed and are treated as untrusted text.
- SQLite incidents, diagnosis history, status, attempted fixes, and regression/test scenarios.
- Sanitized JSON/CSV exports and CSV formula-injection protection.
- FastAPI interactive docs at `/docs`; no arbitrary production APIs are invoked.

## Requirements

Python 3.10 or later is required (tested here with Python 3.12). VS Code is recommended for Windows. The app itself requires no paid key and no external service. The optional LLM feature requires an OpenAI-compatible endpoint and key.

## Windows setup in VS Code (Command Prompt)

1. Install Python 3.10+ from [python.org](https://www.python.org/downloads/) and select **Add Python to PATH**. Check it in Command Prompt:

   ```bat
   python --version
   ```

2. Open VS Code, choose **File → Open Folder…**, and select the `AI_API_Diagnosis` folder. Open **Terminal → New Terminal** and select Command Prompt if necessary.

3. Create and activate a virtual environment:

   ```bat
   python -m venv .venv
   .venv\Scripts\activate
   ```

   If PowerShell is selected instead, use `.venv\Scripts\Activate.ps1`; Windows may require enabling local script execution for the current user. Command Prompt avoids that PowerShell policy issue.

4. Install the dependencies:

   ```bat
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

5. Create the environment file. In Command Prompt:

   ```bat
   copy .env.example .env
   ```

   Leave `LLM_API_KEY` empty for local rules. For optional AI, edit `.env` and set `LLM_API_KEY`, and optionally `LLM_BASE_URL` and `LLM_MODEL`. Do not commit `.env`.

6. Initialize the SQLite database. Starting the backend initializes it automatically. To initialize explicitly:

   ```bat
   python -c "from backend.database import init_db; init_db(); print('SQLite database initialized')"
   ```

7. Start the FastAPI backend in the first terminal:

   ```bat
   .venv\Scripts\activate
   uvicorn backend.main:app --reload
   ```

   Verify `http://127.0.0.1:8000/health`; interactive API documentation is at `http://127.0.0.1:8000/docs`.

8. Open a second VS Code terminal, activate the same environment, and start Streamlit:

   ```bat
   .venv\Scripts\activate
   streamlit run frontend/dashboard.py
   ```

9. Open the URL shown by Streamlit, normally `http://localhost:8501`.

10. Run the tests from the project root:

   ```bat
   python -m pytest -q
   ```

## Demo documentation and workflow

Use **Documentation Library** to upload `docs/sample_api_spec.json`. Create an incident, inspect and confirm the sanitized preview, then go to **Diagnose Error**. The diagnosis will retrieve relevant documentation passages and show their filename and line-range source reference. Record fixes, status changes, and test scenarios from their corresponding pages.

To create an optional synthetic sample incident from the project root, activate the virtual environment and run:

```bat
python seed_demo.py
```

This initializes the database and prints the ID of the synthetic incident it creates. Re-running creates a separate synthetic example with a new ID.

## API endpoints

- `GET /health`
- `POST /incidents`
- `GET /incidents` (search, status/category/status-code filters, limit, offset)
- `GET /incidents/{incident_id}`
- `POST /incidents/{incident_id}/diagnose`
- `PATCH /incidents/{incident_id}/status`
- `POST /incidents/{incident_id}/fix-attempts`
- `POST /documents/upload`; `GET /documents`
- `POST /incidents/{incident_id}/test-scenarios`
- `GET /incidents/{incident_id}/export?format=json|csv`

## GitHub without private data

Create a new repository on GitHub, then from this project folder:

```bat
git init
git add .
git status
git commit -m "Build API error diagnosis assistant"
git branch -M main
git remote add origin https://github.com/YOUR_ACCOUNT/YOUR_REPOSITORY.git
git push -u origin main
```

Before `git add`, verify `.env` is not staged and inspect `git status`. `.gitignore` excludes environment secrets, SQLite database files, local data, uploads, virtual environments, and editor state. Keep only synthetic sample material in version control. If sensitive content was ever committed, removing it in a later commit is insufficient; revoke/rotate the secret and follow GitHub history-cleanup guidance.

## Deployment notes

No deployment is performed by this project. For a private deployment, use a host that supports Python web processes and persistent storage. Configure the Streamlit frontend and FastAPI backend as separate services (or use a private reverse proxy), set `API_BASE_URL` to the backend’s private service URL, configure optional LLM variables through the host’s secret manager, and mount persistent storage for `DATABASE_PATH`/`APP_DATA_DIR`. Restrict public access at the network/proxy layer and terminate TLS at a trusted proxy. Do not expose the unauthenticated app to the public internet. SQLite is appropriate for local/small single-instance use; multi-user/high-availability deployments should adopt an authenticated architecture and a managed database. Keep uploads and incident data private and backed up securely.

## Troubleshooting

- **Streamlit cannot connect:** make sure the backend is running and `/health` works; set `API_BASE_URL` if using a non-default local port.
- **`ModuleNotFoundError`:** activate `.venv` and reinstall with `python -m pip install -r requirements.txt` from the project root.
- **Upload rejected:** only TXT, Markdown, JSON, YAML are supported; default limit is 2 MB (`MAX_UPLOAD_BYTES`).
- **No source references:** upload approved documentation and run diagnosis again. Lexical retrieval returns passages only when there are matching terms.
- **AI unavailable:** local rule-based diagnosis remains available; check optional provider base URL, model, key, and connectivity. Provider details are intentionally not surfaced in full to avoid accidental disclosure.
- **Port already in use:** run `uvicorn backend.main:app --reload --port 8001` and set `API_BASE_URL=http://127.0.0.1:8001` before launching Streamlit.

## Known limitations and security notes

Masking relies on common field names and patterns; it can miss secrets, encoded values, custom credential formats, or personal data. Redaction is applied before persistence and AI calls, and repeated on export, but it is not a guarantee. Uploaded documentation is stored as text passages in SQLite; no document deletion endpoint, encryption at rest, user authentication, or multi-tenant access control is included. The basic lexical retriever is intentionally lightweight and may miss semantically relevant passages. Diagnosis does not call real APIs or prove root causes. The optional provider receives only the app’s sanitized incident and retrieved passages but remains an external data processor. Review and authorize the provider before enabling it.

## Verification record

The source includes pytest tests for redaction, parser behavior, all classification categories, rule fallback, retrieval references, persistence, input validation, fix/scenario tracking, API health, and sanitized exports. Run `python -m pytest -q` in your environment for the current execution result; test execution status is reported separately with the delivered build.
