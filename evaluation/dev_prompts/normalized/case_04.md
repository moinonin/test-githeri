Build a FastAPI API for managing user accounts.
Fields: id, username (unique), email (unique), password_hash, role, is_active, created_at.
Endpoints: POST /users (register), GET /users, GET /users/{id}, PUT /users/{id}, DELETE /users/{id}, POST /users/{id}/deactivate, GET /health.
Rules: username and email unique; password hashed; only admin role can delete.
Use Python, FastAPI, SQLAlchemy 2.x, PostgreSQL, pytest.
The task is complete when the application starts in a clean environment, migrations execute, and automated tests pass.

Authenticated users may manage only their own records; access to foreign resources must be rejected with HTTP 403 or 404. Reject invalid inputs (422), unauthenticated requests (401), unauthorized actions (403), and missing resources (404).
