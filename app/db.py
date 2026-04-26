from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_url TEXT NOT NULL,
    caption TEXT NOT NULL,
    media_type TEXT NOT NULL DEFAULT 'REEL',
    trial_graduation_strategy TEXT,
    publish_at TEXT NOT NULL,
    status TEXT NOT NULL,
    meta_creation_id TEXT,
    meta_media_id TEXT,
    last_error TEXT,
    replacement_for_job_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS manual_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_path TEXT NOT NULL,
    caption TEXT NOT NULL,
    publish_at TEXT NOT NULL,
    status TEXT NOT NULL,
    browser_command TEXT,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(jobs)").fetchall()
            }
            if "trial_graduation_strategy" not in columns:
                connection.execute(
                    "ALTER TABLE jobs ADD COLUMN trial_graduation_strategy TEXT"
                )
            if "media_type" not in columns:
                connection.execute(
                    "ALTER TABLE jobs ADD COLUMN media_type TEXT NOT NULL DEFAULT 'REEL'"
                )
            if "replacement_for_job_id" not in columns:
                connection.execute(
                    "ALTER TABLE jobs ADD COLUMN replacement_for_job_id INTEGER"
                )
            manual_tables = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            if "manual_jobs" not in manual_tables:
                connection.executescript(
                    """
                    CREATE TABLE manual_jobs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        video_path TEXT NOT NULL,
                        caption TEXT NOT NULL,
                        publish_at TEXT NOT NULL,
                        status TEXT NOT NULL,
                        browser_command TEXT,
                        last_error TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    """
                )
