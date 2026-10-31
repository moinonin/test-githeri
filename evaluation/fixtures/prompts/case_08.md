Build a FastAPI API for managing subscriptions.
Fields: id, user_id, plan, status, start_date, end_date, auto_renew.
Endpoints: POST /subscriptions, GET /subscriptions, GET /subscriptions/{id}, PUT /subscriptions/{id} (cancel/renew), DELETE /subscriptions/{id}, GET /health.
Rules: status in active/cancelled/expired; end_date after start_date; auto_renew boolean.
Use Python, FastAPI, SQLAlchemy 2.x, SQLite, pytest.
The task is complete when the application starts in a clean environment, migrations execute, and automated tests pass.