Build a FastAPI API for managing file metadata.
Fields: id, filename, content_type, size_bytes, owner_id, uploaded_at.
Endpoints: POST /files (metadata only), GET /files, GET /files/{id}, DELETE /files/{id}, GET /health.
Rules: size_bytes non-negative; filename required.
Use Python, FastAPI, SQLAlchemy 2.x, SQLite, pytest.
The task is complete when the application starts in a clean environment, migrations execute, and automated tests pass.

Reject invalid inputs (422), unauthenticated requests (401), unauthorized actions (403), and missing resources (404).
