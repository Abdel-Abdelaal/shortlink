# AGENTS.md

FastAPI URL shortener. The engineering around it (CI, security, governance) is the point; keep the app small and clean.

## Commands
- Install: `uv sync` (Windows local: `python -m uv sync`)
- Run: `uv run fastapi dev src/shortlink/main.py`
- Test: `uv run pytest --cov`
- Lint/format: `uv run ruff check --fix . && uv run ruff format .`
- Types: `uv run pyright`
- Hooks: `uv run pre-commit install`

## Rules
Follow the handbook: https://github.com/Abdel-Abdelaal/.github/tree/main/standards
(python.md for code, commits.md for messages, code-review.md for review comments).
- `domain/` never imports FastAPI, sqlite3 or anything in `api/` or `db/`.
- Domain errors are mapped to HTTP in `api/errors.py` only.
- Every change needs tests. Coverage must stay at or above 90%.

## Glossary

one name per concept; use exactly these.
| Name | Meaning | Never call it |
|---|---|---|
| link | a stored mapping from a code to a target URL | url, mapping, entry, record |
| code | the short identifier in the path, e.g. `abc123` | slug, key, id, short_id, hash |
| target_url | where a link redirects | long_url, original_url, destination, url |
| short_url | `base_url` + `/` + code | link_url, tiny_url |
| hits | number of successful redirects | clicks, visits, count, views |
| expires_at | UTC time after which the link returns 410 | expiry, ttl, expiration |
| created_at | UTC creation time | created, timestamp |
