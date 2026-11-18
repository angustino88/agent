import pandas as pd
from typing import Any
from datetime import datetime
from src.utils.sqlite_db import SQLiteDatabase

class SessionLogger(SQLiteDatabase):
    """SQLite logger for lab sessions and status events."""

    def __init__(self, db_path: str, autocommit: bool = True):
        super().__init__(db_path, autocommit=autocommit)
        self.connect()

    # ----------------- Session Log -----------------
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
            """
        )

    def insert_session_log(self, *args: Any) -> None:
        self.insert("session_log", [args])

    def export_session_log(self, file_path: str) -> None:
        df = pd.read_sql("SELECT * FROM session_log", self._con)
        df.to_excel(file_path, index=False)

    # ----------------- Status Log -----------------
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
            """
        )

    def insert_status_log(self, lab_computer: str, status: str,
                          remote_user: str, remote_user_displayname: str,
                          remote_computer: str, remote_ip: str) -> None:
        now = datetime.now().isoformat()
        self.insert("status_log", [
            (lab_computer, now, status, remote_user,
             remote_user_displayname, remote_computer, remote_ip)
        ])

    def export_status_log(self, file_path: str) -> None:
        df = pd.read_sql("SELECT * FROM status_log", self._con)
        df.to_excel(file_path, index=False)
