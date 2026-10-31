Build a Flask REST API for managing blog posts.
Fields: id, title, body, author, published, created_at, updated_at.
Endpoints: POST /posts, GET /posts (filter by author/published, paginate), GET /posts/{id}, PUT /posts/{id}, DELETE /posts/{id}, GET /health.
Rules: title required non-empty; published defaults false; author required.
Use Python, Flask, SQLAlchemy 2.x, PostgreSQL, pytest.
The task is complete when the application starts in a clean environment, migrations execute, and automated tests pass.