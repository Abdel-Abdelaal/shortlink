"""Store links with parameterized SQLite queries and atomic hit updates."""

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from shortlink.domain.errors import CodeTakenError, LinkNotFoundError
from shortlink.domain.models import Link


class SqliteLinkRepository:
    """Open a short-lived connection for each operation for thread safety."""

    def __init__(self, database_path: Path) -> None:
        """Remember the database path without performing import-time I/O."""
        self._database_path = database_path

    def initialize(self) -> None:
        """Create the parent directory and schema at application startup."""
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS links ("
                "code TEXT PRIMARY KEY, target_url TEXT NOT NULL, "
                "created_at TEXT NOT NULL, expires_at TEXT, "
                "hits INTEGER NOT NULL DEFAULT 0)"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def add(self, link: Link) -> None:
        """Store a link, translating primary-key collisions to the domain error."""
        with closing(self._connect()) as connection, connection:
            try:
                connection.execute(
                    "INSERT INTO links VALUES (?, ?, ?, ?, ?)",
                    (
                        link.code,
                        link.target_url,
                        link.created_at.astimezone(UTC).isoformat(),
                        link.expires_at.astimezone(UTC).isoformat()
                        if link.expires_at is not None
                        else None,
                        link.hits,
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise CodeTakenError from error

    def get(self, code: str) -> Link:
        """Read a link with UTC-aware timestamps, or raise LinkNotFoundError."""
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT code, target_url, created_at, expires_at, hits "
                "FROM links WHERE code = ?",
                (code,),
            ).fetchone()
        if row is None:
            raise LinkNotFoundError
        return Link(
            code=str(row["code"]),
            target_url=str(row["target_url"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            expires_at=datetime.fromisoformat(str(row["expires_at"]))
            if row["expires_at"] is not None
            else None,
            hits=int(row["hits"]),
        )

    def increment_hits(self, code: str) -> None:
        """Increment in SQL so concurrent redirects cannot lose counts."""
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                "UPDATE links SET hits = hits + 1 WHERE code = ?", (code,)
            )
            if cursor.rowcount == 0:
                raise LinkNotFoundError

    def delete(self, code: str) -> None:
        """Delete one link and report absent codes without silently succeeding."""
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute("DELETE FROM links WHERE code = ?", (code,))
            if cursor.rowcount == 0:
                raise LinkNotFoundError
