Build a FastAPI API for managing invoices.
Fields: id, customer_name, amount, currency, due_date, paid, created_at.
Endpoints: POST /invoices, GET /invoices (filter by paid/due_date), GET /invoices/{id}, PUT /invoices/{id} (mark paid), DELETE /invoices/{id}, GET /health.
Rules: amount positive; currency 3-letter code; paid defaults false.
Use Python, FastAPI, SQLAlchemy 2.x, SQLite, pytest.
The task is complete when the application starts in a clean environment, migrations execute, and automated tests pass.