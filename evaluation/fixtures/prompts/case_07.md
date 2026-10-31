Build a FastAPI API for managing appointments.
Fields: id, patient_name, doctor_name, start_time, end_time, status, notes.
Endpoints: POST /appointments, GET /appointments (filter by doctor/date), GET /appointments/{id}, PUT /appointments/{id}, DELETE /appointments/{id}, GET /health.
Rules: no overlapping appointments for same doctor; end_time after start_time; status in scheduled/completed/cancelled.
Use Python, FastAPI, SQLAlchemy 2.x, PostgreSQL, pytest.
The task is complete when the application starts in a clean environment, migrations execute, and automated tests pass.