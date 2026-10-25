Software Request

1. Objective

I want to build a REST API for managing support-engineer follow-up tasks, to solve the current
practice of tracking customer follow-ups in shared spreadsheets, which causes missed deadlines and
provides no audit trail.

2. Users and Context

The intended users are internal support engineers and their team leads, accessed through an
internal API client. They need to be able to record a follow-up task the moment a customer
interaction happens, and to retrieve the current state of their team's workload at any time.

3. Required Functionality

The system must allow users to:

 • Create a task (POST /tasks) with title, description, status, and due_date
 • List tasks (GET /tasks) with optional status filter and limit/offset pagination
 • Fetch a single task (GET /tasks/{task_id})
 • Update a task (PUT /tasks/{task_id})
 • Delete a task (DELETE /tasks/{task_id})
 • Check liveness (GET /health)

4. Data and Business Rules

The system must manage tasks, each having: id (server-assigned integer), title (non-empty string),
description (optional string), status (enum: todo, in_progress, done), due_date (optional ISO-8601
date), created_at and updated_at timestamps.

The following rules must be enforced:

 • A newly created task always has status "todo" regardless of client input
 • A task may only transition between statuses todo, in_progress, and done
 • Updating a task that does not exist must fail with HTTP 404
 • Deleting a task that does not exist must fail with HTTP 404

5. Constraints

Use Python 3.11 with FastAPI, SQLAlchemy 2.x, and SQLite for local runs. Use pytest for testing.
The implementation must respect: no authentication in this phase, no background workers, no
external service dependencies, and no frontend.

6. Failure and Edge Cases

The system must handle:

 • Invalid inputs: missing or empty title, invalid status value, malformed date -> HTTP 422
 • Missing resources: requests for non-existent task IDs return HTTP 404
 • Duplicate creates: creating a task with a client-supplied duplicate id returns HTTP 409
 • Empty collections: listing with no tasks returns an empty JSON array, not null

7. Verification

Include automated tests that verify:

 • Each of the six endpoints, happy path and rejection path
 • That a created task is persisted and retrievable from the database
 • That status defaults to "todo" on create and that invalid transitions are rejected
 • That list filtering by status and pagination bounds are honoured

8. Completion Criteria

The work is complete when:

 • The application starts cleanly in a fresh environment with only requirements.txt installed
 • Database migrations execute successfully against an empty database
 • The automated test suite passes with zero failures
 • A liveness probe returns HTTP 200 with the service name
