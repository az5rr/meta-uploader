from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    meta_access_token: str
    meta_ig_user_id: str
    meta_graph_version: str = "v24.0"
    meta_poll_seconds: int = 5
    meta_publish_limit: int = 100
    scheduler_interval_seconds: int = 5
    scheduler_lead_seconds: int = 30
    database_path: str = "meta_uploader.db"

    @property
    def graph_base_url(self) -> str:
        return f"https://graph.instagram.com/{self.meta_graph_version}"


def _read_env_file(path: str) -> None:
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def get_settings() -> Settings:
    _read_env_file(".env")
    _read_env_file(os.path.join(os.path.dirname(__file__), "..", ".env"))

    access_token = os.environ.get("META_ACCESS_TOKEN", "").strip()
    ig_user_id = os.environ.get("META_IG_USER_ID", "").strip()

    if not access_token:
        raise RuntimeError("META_ACCESS_TOKEN is required")
    if not ig_user_id:
        raise RuntimeError("META_IG_USER_ID is required")

    return Settings(
        meta_access_token=access_token,
        meta_ig_user_id=ig_user_id,
        meta_graph_version=os.environ.get("META_GRAPH_VERSION", "v24.0"),
        meta_poll_seconds=int(os.environ.get("META_POLL_SECONDS", "5")),
        meta_publish_limit=int(os.environ.get("META_PUBLISH_LIMIT", "100")),
        scheduler_interval_seconds=int(os.environ.get("SCHEDULER_INTERVAL_SECONDS", "5")),
        scheduler_lead_seconds=int(os.environ.get("SCHEDULER_LEAD_SECONDS", "30")),
        database_path=os.environ.get("DATABASE_PATH", "meta_uploader.db"),
    )
