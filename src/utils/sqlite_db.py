"""SQLite database access utilities."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable


class SQLiteDatabase:
    """Base class for SQLite database access with auto-commit support."""

    def __init__(self, db_path: str, autocommit: bool = True):
        self._db_path = Path(db_path)
        self._autocommit = autocommit
        self._con: sqlite3.Connection | None = None
        self._cur: sqlite3.Cursor | None = None

    @property
    def connected(self) -> bool:
        """Return ``True`` if the connection is open."""
        return self._con is not None

    def connect(self) -> None:
        self._con = sqlite3.connect(self._db_path)
        self._con.row_factory = sqlite3.Row
        self._cur = self._con.cursor()

    def reconnect(self) -> None:
        self.close()
        self.connect()

    def close(self) -> None:
        if self._con:
            if self._autocommit:
                self._con.commit()
            self._con.close()
        self._con, self._cur = None, None

    def __enter__(self) -> SQLiteDatabase:
        return self

    def __exit__(self, exc_type: type | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        if exc_type:
            if self._con:
                self._con.rollback()
        elif self._autocommit and self._con:
            self._con.commit()
        self.close()

    def commit(self) -> None:
        if self._con:
            self._con.commit()

    def execute(self, query: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        try:
            self._cur.execute(query, tuple(params))
        except sqlite3.ProgrammingError:
            self.reconnect()
            self._cur.execute(query, tuple(params))
        return self._cur

    def executemany(self, query: str, params: Iterable[Iterable[Any]]) -> sqlite3.Cursor:
        try:
            self._cur.executemany(query, params)
        except sqlite3.ProgrammingError:
            self.reconnect()
            self._cur.executemany(query, params)
        return self._cur

    def fetch_one(self, query: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
        cur = self.execute(query, params)
        return cur.fetchone()

    def fetch_all(self, query: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        cur = self.execute(query, params)
        return cur.fetchall()

    def table_exists(self, table: str) -> bool:
        row = self.fetch_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        )
        return row is not None

    def create_table(self, table: str, cols: str) -> None:
        self.execute(f"CREATE TABLE IF NOT EXISTS {table} ({cols})")
        if self._autocommit:
            self._con.commit()

    def insert(self, table: str, rows: list[tuple[Any, ...]]) -> None:
        if not rows:
            return
        placeholders = ",".join("?" * len(rows[0]))
        self.executemany(f"INSERT INTO {table} VALUES ({placeholders})", rows)
        if self._autocommit:
            self._con.commit()