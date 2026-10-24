---
status: accepted
date: 2026-10-24
---

# Use FastAPI, SQLite and uv for the first service

## Context and problem statement

The showcase needs a small real service whose engineering controls can be tested.
It should be runnable without hosted infrastructure while keeping business logic
separate from the framework and persistence implementation.

## Considered options

- FastAPI with SQLite and a domain service.
- A larger framework with PostgreSQL.
- A mock-only service without persistent behavior.

## Decision outcome

Use FastAPI/Pydantic at the HTTP boundary, a framework-independent domain, a
repository protocol and SQLite adapter. uv locks both runtime and developer tools.
The clock is injectable so expiry tests have no sleeps. Hit updates use SQL
increments rather than read/modify/write to avoid lost concurrent updates.

### Consequences

- The app runs locally and tests exercise real SQLite with temporary databases.
- SQLite is appropriate for a single-instance demo; distributed deployments need
  a shared database, backups and migration strategy before horizontal scaling.
- This is an unauthenticated educational service: anyone with a code can query
  or delete it. Add authentication, authorization, quotas and abuse prevention
  before exposing it as a public multi-user service.
- Reserved route names cannot be chosen as custom codes. The configured origin,
  rather than the request Host header, supplies public short URLs.
