"""PostgreSQL database access utilities."""
from __future__ import annotations

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Iterable


class PostgresDatabase:
    """Base class for PostgreSQL access with context-manager and transaction support."""

    def __init__(self, dsn: str, autocommit: bool = True):
        self._dsn = dsn
        self._autocommit = autocommit
        self._con: psycopg2.extensions.connection | None = None
        self._cur: psycopg2.extensions.cursor | None = None

    @property
    def connected(self) -> bool:
        """Return ``True`` if the connection is open."""
        return self._con is not None and not self._con.closed

    def connect(self) -> None:
        self._con = psycopg2.connect(self._dsn, cursor_factory=RealDictCursor)
        self._cur = self._con.cursor()
        self._con.autocommit = self._autocommit

    def reconnect(self) -> None:
        """Reconnect safely."""
        self.close()
        self.connect()

    def close(self):
        """Close the connection."""
        if self._cur:
            self._cur.close()
        if self._con:
            self._con.close()
        self._cur, self._con = None, None

    def __enter__(self) -> "PostgresDatabase":
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            self.rollback()
        else:
            if self._autocommit:
                self.commit()
        self.close()

    def begin(self):
        """Start a manual transaction."""
        if self._con:
            self._con.autocommit = False

    def commit(self):
        if self._con:
            self._con.commit()
            self._con.autocommit = self._autocommit

    def rollback(self):
        if self._con:
            self._con.rollback()
            self._con.autocommit = self._autocommit

    def execute(self, query: str, params: tuple = ()):
        """Execute a query safely, reconnect if necessary."""
        try:
            self._cur.execute(query, params)
        except psycopg2.OperationalError:
            self.reconnect()
            self._cur.execute(query, params)
        return self._cur

    def executemany(self, query: str, params_list: Iterable[tuple]):
        """Execute a query with multiple sets of parameters."""
        try:
            self._cur.executemany(query, params_list)
        except psycopg2.OperationalError:
            self.reconnect()
            self._cur.executemany(query, params_list)
        return self._cur

    def fetch_one(self, query: str, params: tuple = ()):
        self.execute(query, params)
        return self._cur.fetchone()

    def fetch_all(self, query: str, params: tuple = ()):
        self.execute(query, params)
        return self._cur.fetchall()

    def table_exists(self, table: str) -> bool:
        row = self.fetch_one(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name=%s)",
            (table,)
        )
        return row["exists"]

    def insert(self, table: str, rows: Iterable[tuple], columns: Iterable[str] | None = None):
        """Insert multiple rows into a table."""
        rows = list(rows)
        if not rows:
            return

        if columns:
            col_names = ",".join(columns)
        else:
            col_names = ",".join(f"col{i+1}" for i in range(len(rows[0])))

        placeholders = ",".join(["%s"] * len(rows[0]))
        query = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"
        self.executemany(query, rows)
        if self._autocommit:
            self._con.commit()