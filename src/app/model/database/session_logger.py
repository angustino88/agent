from datetime import datetime
from typing import Optional

import pandas as pd

from src.app.model.types.remote_session import RemoteSession
from src.utils.sqlite_db import SQLiteDatabase


class SessionLogger(SQLiteDatabase):
    """Local SQLite log of remote sessions and activity status changes.

    Column names are a stored format kept from earlier versions (``lab_computer``,
    ``remote_user_displayname``) so existing log databases keep working.
    """

    def __init__(self, db_path: str, autocommit: bool = True):
        super().__init__(db_path, autocommit=autocommit)
        self.connect()

    # ----------------- Session log -----------------
    def create_session_log(self) -> None:
        self.create_table(
            "session_log",
            """
            lab_computer TEXT,
            login_time TEXT,
            logout_time TEXT,
            duration INTEGER,
            active_time INTEGER,
            booking_code TEXT,
            remote_user TEXT,
            remote_user_displayname TEXT,
            remote_computer TEXT,
            remote_ip TEXT
            """,
        )

    def insert_session_log(
        self, session: RemoteSession, login_at: datetime, logout_at: datetime, active_seconds: float
    ) -> None:
        """Durations are stored in minutes."""
        total_minutes = int((logout_at - login_at).total_seconds() // 60)
        self.insert(
            "session_log",
            [
                (
                    session.computer_name,
                    login_at.isoformat(),
                    logout_at.isoformat(),
                    total_minutes,
                    int(active_seconds // 60),
                    session.booking_code or "",
                    session.remote_user,
                    session.remote_user_display_name,
                    session.remote_computer,
                    session.remote_ip,
                )
            ],
        )

    def export_session_log(self, file_path: str) -> None:
        pd.read_sql("SELECT * FROM session_log", self._con).to_excel(file_path, index=False)

    # ----------------- Status log -----------------
    def create_status_log(self) -> None:
        self.create_table(
            "status_log",
            """
            lab_computer TEXT,
            datetime TEXT,
            status TEXT,
            remote_user TEXT,
            remote_user_displayname TEXT,
            remote_computer TEXT,
            remote_ip TEXT
            """,
        )

    def insert_status_log(self, computer_name: str, status: str, session: Optional[RemoteSession]) -> None:
        self.insert(
            "status_log",
            [
                (
                    computer_name,
                    datetime.now().isoformat(),
                    status,
                    session.remote_user if session else "-",
                    session.remote_user_display_name if session else "-",
                    session.remote_computer if session else "-",
                    session.remote_ip if session else "-",
                )
            ],
        )

    def export_status_log(self, file_path: str) -> None:
        pd.read_sql("SELECT * FROM status_log", self._con).to_excel(file_path, index=False)
