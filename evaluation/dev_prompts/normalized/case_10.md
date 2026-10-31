Build a FastAPI API for managing tasks in a project tracker.
Fields: id, project_id, title, assignee, priority, status, due_date.
Endpoints: POST /tasks, GET /tasks (filter by project/status/assignee), GET /tasks/{id}, PUT /tasks/{id}, DELETE /tasks/{id}, GET /health.
Rules: priority in low/medium/high; status in todo/in_progress/done/blocked; title required.
Use Python, FastAPI, SQLAlchemy 2.x, SQLite, pytest.
The task is complete when the application starts in a clean environment, migrations execute, and automated tests pass.

Reject invalid inputs (422), unauthenticated requests (401), unauthorized actions (403), and missing resources (404).
