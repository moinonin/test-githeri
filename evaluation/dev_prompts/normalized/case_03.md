Build a Starlette async API for managing events.
Fields: id, name, start_time, end_time, location, capacity, attendees.
Endpoints: POST /events, GET /events, GET /events/{id}, PUT /events/{id}, DELETE /events/{id}, POST /events/{id}/register, GET /health.
Rules: end_time after start_time; capacity >= attendees; registration fails when full.
Use Python, Starlette, Tortoise ORM, SQLite, pytest-asyncio.
The task is complete when the application starts in a clean environment, migrations execute, and automated tests pass.

Reject invalid inputs (422), unauthenticated requests (401), unauthorized actions (403), and missing resources (404).
