#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from app.config import get_settings
from app.db import Database
from app.meta_api import MetaApiClient
from app.service import JobService


DEFAULT_BROWSER_SCRIPT = os.environ.get("META_BROWSER_ASSIST_SCRIPT", "meta_business_suite_scheduler.py")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Open the next queued manual Meta-Uploader job in the semi-automatic Business Suite flow."
    )
    parser.add_argument("--job-id", type=int, help="Open a specific manual job id.")
    parser.add_argument(
        "--browser-script",
        default=DEFAULT_BROWSER_SCRIPT,
        help="Path to the browser-assist scheduler script.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = get_settings()
    service = JobService(Database(settings.database_path), MetaApiClient(settings), settings)

    if args.job_id is not None:
        try:
            job = service.get_manual_job(args.job_id)
        except KeyError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    else:
        job = service.next_manual_job()
        if job is None:
            print("No scheduled manual jobs found.")
            return 0

    browser_script = Path(args.browser_script).expanduser().resolve()
    if not browser_script.exists():
        print(f"Browser assist script not found: {browser_script}", file=sys.stderr)
        service.update_manual_job(job["id"], status="failed", last_error="browser assist script not found")
        return 1

    publish_at = datetime.fromisoformat(job["publish_at"])
    command = [
        sys.executable,
        str(browser_script),
        "--manual-after-caption",
        "--keep-open",
        "--type",
        "reel",
        "--media",
        job["video_path"],
        "--caption",
        job["caption"],
        "--date",
        publish_at.strftime("%Y-%m-%d"),
        "--time",
        publish_at.strftime("%H:%M"),
    ]
    command_text = shlex.join(command)

    service.update_manual_job(
        job["id"],
        status="opening",
        browser_command=command_text,
        last_error=None,
    )

    print(f"Opening manual job {job['id']}")
    print(f"Video: {job['video_path']}")
    print(f"Publish at: {job['publish_at']}")
    print(f"Command: {command_text}")

    completed = subprocess.run(command).returncode
    if completed == 0:
        service.update_manual_job(
            job["id"],
            status="ready_for_manual_completion",
            browser_command=command_text,
            last_error=None,
        )
        return 0

    service.update_manual_job(
        job["id"],
        status="failed",
        browser_command=command_text,
        last_error=f"browser assist exited with code {completed}",
    )
    return completed


if __name__ == "__main__":
    raise SystemExit(main())
