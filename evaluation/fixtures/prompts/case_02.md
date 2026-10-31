Build a Django REST API for managing customer orders.
Fields: id, customer_name, items (list), total_amount, status, created_at.
Endpoints: POST /orders, GET /orders (filter by status/date), GET /orders/{id}, PATCH /orders/{id} (status transition), DELETE /orders/{id}, GET /health.
Rules: status transitions pending->shipped->delivered only; total_amount must be positive.
Use Python, Django, Django ORM, PostgreSQL, pytest.
The task is complete when the application starts in a clean environment, migrations execute, and automated tests pass.