Build a FastAPI REST API for managing an inventory of warehouse items.

Requirements:
- Item fields: id, sku (unique), name, quantity, location, created_at, updated_at.
- Create item (POST /items). SKU must be unique; duplicate returns 409.
- List items (GET /items) with optional filters: location, low_stock (quantity below threshold), pagination via limit/offset.
- Get item by id (GET /items/{item_id}) returns 404 if missing.
- Update item (PUT /items/{item_id}) partial update; 404 if missing.
- Delete item (DELETE /items/{item_id}) returns 204; 404 if missing.
- Health check (GET /health) returns {"status": "ok", "service": "inventory-api"}.
- Newly created item defaults quantity to 0.
- Business rules:
  - SKU uniqueness enforced.
  - Quantity cannot be negative.
  - Low-stock threshold is 5.

Use Python, FastAPI, SQLAlchemy 2.x, SQLite, pytest.

The task is complete when the application starts in a clean environment, migrations execute, and automated tests pass.
