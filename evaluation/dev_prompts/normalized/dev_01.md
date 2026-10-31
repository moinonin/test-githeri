Build a FastAPI REST API for tracking support tickets.

Fields: id, title, description, priority, status, assignee, created_at, updated_at.
Endpoints:
- POST /tickets (create)
- GET /tickets (list, filter by status/priority/assignee, paginate)
- GET /tickets/{ticket_id} (404 if missing)
- PUT /tickets/{ticket_id} (partial update; 404 if missing)
- DELETE /tickets/{ticket_id} (204; 404 if missing)
- GET /health returns {"status": "ok", "service": "support-tickets-api"}

Rules:
- title required non-empty.
- priority in low/medium/high/urgent.
- status in open/in_progress/resolved/closed.
- status transitions: open -> in_progress -> resolved -> closed.
- assignee required.
- Reject invalid inputs (422), missing resources (404).
- Duplicate title for same assignee returns 409.

Use Python, FastAPI, SQLAlchemy 2.x, SQLite, pytest.
Include automated integration tests exercising actual API endpoints and database persistence.
The task is complete when the application starts in a clean environment, migrations execute, and automated tests pass.
