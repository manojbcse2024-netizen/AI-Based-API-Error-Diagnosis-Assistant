import re
from collections import Counter
from pathlib import Path
from typing import Any
from backend.database import get_connection
from backend.security import redact_text

SUPPORTED_EXTENSIONS = {".txt", ".md", ".json", ".yaml", ".yml"}
TOKEN_RE = re.compile(r"[A-Za-z0-9_./-]{2,}")


def split_passages(text: str, max_chars: int = 900) -> list[tuple[str, str]]:
    lines = text.splitlines()
    passages: list[tuple[str, str]] = []
    buffer: list[str] = []
    start_line = 1
    current_len = 0
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        if current_len + len(line) > max_chars and buffer:
            passages.append((f"lines {start_line}-{i-1}", "\n".join(buffer)))
            buffer, current_len, start_line = [], 0, i
        buffer.append(line)
        current_len += len(line) + 1
    if buffer:
        passages.append((f"lines {start_line}-{len(lines)}", "\n".join(buffer)))
    return passages


def index_document(filename: str, content: bytes) -> dict[str, Any]:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError("Unsupported document type")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("File must be UTF-8 text") from exc
    text = redact_text(text[:2_000_000])
    chunks = split_passages(text)
    if not chunks:
        raise ValueError("The document contains no readable text")
    with get_connection() as conn:
        for ref, passage in chunks:
            conn.execute("INSERT INTO documents(filename, source_ref, passage, created_at) VALUES(?,?,?,datetime('now'))",
                         (Path(filename).name, ref, passage))
    return {"filename": Path(filename).name, "passages_indexed": len(chunks)}


def retrieve(query: str, limit: int = 5) -> list[dict[str, str]]:
    query_terms = set(t.lower() for t in TOKEN_RE.findall(query))
    if not query_terms:
        return []
    with get_connection() as conn:
        rows = conn.execute("SELECT filename, source_ref, passage FROM documents").fetchall()
    ranked = []
    for row in rows:
        terms = [t.lower() for t in TOKEN_RE.findall(row["passage"])]
        counts = Counter(terms)
        score = sum(counts[t] for t in query_terms)
        if score:
            ranked.append((score, {"filename": row["filename"], "reference": row["source_ref"], "passage": row["passage"]}))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [obj for _, obj in ranked[:limit]]


def list_documents() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT filename, COUNT(*) AS passages, MIN(created_at) AS added_at FROM documents GROUP BY filename ORDER BY added_at DESC").fetchall()
    return [dict(row) for row in rows]
