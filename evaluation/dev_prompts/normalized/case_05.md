Build an aiohttp API for managing product reviews.
Fields: id, product_id, user_id, rating (1-5), comment, created_at.
Endpoints: POST /reviews, GET /reviews (filter by product_id/rating), GET /reviews/{id}, PUT /reviews/{id}, DELETE /reviews/{id}, GET /health.
Rules: rating between 1 and 5; one review per user per product.
Use Python, aiohttp, Peewee, SQLite, pytest-aiohttp.
The task is complete when the application starts in a clean environment, migrations execute, and automated tests pass.

Authenticated users may manage only their own records; access to foreign resources must be rejected with HTTP 403 or 404. Reject invalid inputs (422), unauthenticated requests (401), unauthorized actions (403), and missing resources (404).
