from __future__ import annotations

import os
import re
import sqlite3
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
from datetime import UTC, datetime, timedelta
from typing import Any

from app.config import Settings
from app.db import Database
from app.meta_api import MetaApiClient, MetaApiError
from app.schemas import ManualJobCreate, PublishRequest, PublishingLimitResponse, ScheduledJobCreate


FIXED_REEL_CAPTION = """تُعَدُّ ساعةُ مكةَ المكرمة، المعروفةُ بساعةِ البرجِ الملكي، واحدةً من أبرزِ المعالمِ المعماريةِ والحضاريةِ في المملكةِ العربيةِ السعودية، إذ ترتفعُ شامخةً فوقَ أبراجِ البيتِ لتُعلنَ الوقتَ من قلبِ الحرمِ المكيِّ في مشهدٍ مهيبٍ يجمعُ بينَ عظمةِ الهندسةِ الحديثةِ وروحانيةِ المكانِ وقدسيته، حتى غدت مع مرور السنوات رمزًا بصريًّا يلفتُ أنظارَ الزائرينَ من مختلفِ أنحاءِ العالم لما تتميزُ به من حجمٍ ضخمٍ وإضاءةٍ آسرةٍ وحضورٍ استثنائيٍّ يرسِّخُ في الأذهانِ صورةً مهيبةً لمكةَ المكرمةِ ومكانتها الدينيةِ العظيمة.

وتبرزُ الساعةُ بواجهاتها العملاقةِ وزخارفها الإسلاميةِ الدقيقةِ وتصميمها الفريد الذي يمزجُ بينَ الفخامةِ المعماريةِ والهويةِ الروحية، فتبدو كأنها شاهدٌ دائمٌ على حركةِ الحياةِ والعبادةِ حولَ المسجدِ الحرام، وتمنحُ الأفقَ المكيَّ ملامحَ مميزةً لا تُخطئها العين، خاصةً حين تتلألأ أنوارها في الليلِ فتنعكسُ هيبتُها على المكان وتزيدُ المشهدَ جلالًا وسكينة.

ولا تقتصرُ قيمةُ ساعةِ مكةَ على كونها وسيلةً لبيانِ الوقت، بل أصبحت معلمًا عالميًّا يعكسُ حجمَ العنايةِ التي أُحيطت بها أطهرُ بقاعِ الأرض، كما تجسدُ التقاءَ التقنيةِ الحديثةِ مع الإرثِ الإسلاميِّ في صورةٍ مبهرةٍ تثيرُ التأملَ والإعجاب، وتجعلُ من رؤيتها تجربةً لا تُنسى لكلِّ من قصدَ مكةَ المكرمةَ حاجًّا أو معتمرًا أو زائرًا متطلعًا إلى جمالِ المشهدِ وعظمةِ التفاصيل.

#quran #dua #islam #ذكر #قرآن #مكة #ساعة_مكة #الحرم_المكي #islamic #reels"""
POST_DEFAULT_HASHTAGS = "#dua #islam #quran #تذكير #دعاء #instagram"
CAPTION_CONTROL_TRANSLATION = str.maketrans("", "", "\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\ufeff")
MAX_CAPTION_LENGTH = 2200


def _sanitize_caption_text(caption: str) -> str:
    cleaned = caption.translate(CAPTION_CONTROL_TRANSLATION).replace("\t", " ")
    lines = [re.sub(r"\s+", " ", line).strip() for line in cleaned.splitlines()]

    compact_lines: list[str] = []
    for line in lines:
        if not line:
            if compact_lines and compact_lines[-1] != "":
                compact_lines.append("")
            continue
        compact_lines.append(line)

    while compact_lines and compact_lines[-1] == "":
        compact_lines.pop()

    return "\n".join(compact_lines).strip()


def _truncate_caption(parts: list[str]) -> str:
    caption = "\n\n".join(part for part in parts if part).strip()
    if len(caption) <= MAX_CAPTION_LENGTH:
        return caption

    trimmed: list[str] = []
    current_length = 0
    for part in parts:
        if not part:
            continue
        separator = 2 if trimmed else 0
        remaining = MAX_CAPTION_LENGTH - current_length - separator
        if remaining <= 0:
            break
        candidate = part if len(part) <= remaining else part[: remaining - 1].rstrip() + "…"
        trimmed.append(candidate)
        current_length += separator + len(candidate)
    return "\n\n".join(trimmed).strip()


def _strip_hashtag_lines(caption: str) -> str:
    lines = [line for line in caption.splitlines() if line.strip() and not line.strip().startswith("#")]
    return "\n".join(lines).strip()


def normalize_caption(media_type: str, caption: str) -> str:
    cleaned = _sanitize_caption_text(caption)
    if media_type == "REEL":
        return _sanitize_caption_text(FIXED_REEL_CAPTION)

    if media_type == "POST":
        body = _strip_hashtag_lines(cleaned)
        return _truncate_caption([body, POST_DEFAULT_HASHTAGS]) if body else POST_DEFAULT_HASHTAGS

    return cleaned


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


class JobService:
    def __init__(self, db: Database, meta_client: MetaApiClient, settings: Settings) -> None:
        self.db = db
        self.meta_client = meta_client
        self.settings = settings
        self._lock = threading.Lock()
        self._instagram_metrics_lock = threading.Lock()
        self._instagram_metrics_cache: dict[str, Any] | None = None
        self._instagram_metrics_cached_at: float = 0.0
        self._instagram_metrics_ttl_seconds = 5

    def create_job(self, payload: ScheduledJobCreate) -> dict:
        now = utc_now()
        media_url = payload.video_url
        if payload.media_type == "POST":
            media_url = self._ensure_stable_post_url(payload.video_url, force_restage=True)
        with self.db.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO jobs (
                    video_url, caption, media_type, trial_graduation_strategy, publish_at, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    media_url,
                    normalize_caption(payload.media_type, payload.caption),
                    payload.media_type,
                    payload.trial_params.graduation_strategy if payload.trial_params else None,
                    payload.publish_at.astimezone(UTC).isoformat(),
                    "scheduled",
                    now,
                    now,
                ),
            )
            return self.get_job(cursor.lastrowid, connection)

    def list_jobs(self) -> list[dict]:
        with self.db.connect() as connection:
            rows = connection.execute("SELECT * FROM jobs ORDER BY publish_at ASC, id ASC").fetchall()
            return [dict(row) for row in rows]

    def create_manual_job(self, payload: ManualJobCreate) -> dict:
        now = utc_now()
        with self.db.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO manual_jobs (
                    video_path, caption, publish_at, status, browser_command, last_error, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.video_path,
                    payload.caption,
                    payload.publish_at.isoformat(),
                    "scheduled",
                    None,
                    None,
                    now,
                    now,
                ),
            )
            return self.get_manual_job(cursor.lastrowid, connection)

    def list_manual_jobs(self) -> list[dict]:
        with self.db.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM manual_jobs ORDER BY publish_at ASC, id ASC"
            ).fetchall()
            return [dict(row) for row in rows]

    def get_manual_job(
        self, job_id: int, connection: sqlite3.Connection | None = None
    ) -> dict:
        if connection is None:
            with self.db.connect() as new_connection:
                row = new_connection.execute(
                    "SELECT * FROM manual_jobs WHERE id = ?",
                    (job_id,),
                ).fetchone()
        else:
            row = connection.execute(
                "SELECT * FROM manual_jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Manual job {job_id} not found")
        return dict(row)

    def next_manual_job(self) -> dict | None:
        with self.db.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM manual_jobs
                WHERE status = 'scheduled'
                ORDER BY publish_at ASC, id ASC
                LIMIT 1
                """
            ).fetchone()
            return dict(row) if row is not None else None

    def update_manual_job(
        self,
        job_id: int,
        *,
        status: str,
        browser_command: str | None = None,
        last_error: str | None = None,
    ) -> dict:
        with self.db.connect() as connection:
            connection.execute(
                """
                UPDATE manual_jobs
                SET status = ?, browser_command = COALESCE(?, browser_command), last_error = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, browser_command, last_error, utc_now(), job_id),
            )
            return self.get_manual_job(job_id, connection)

    def get_job(self, job_id: int, connection: sqlite3.Connection | None = None) -> dict:
        if connection is None:
            with self.db.connect() as new_connection:
                row = new_connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        else:
            row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(f"Job {job_id} not found")
        return dict(row)

    def update_job(self, job_id: int, *, status: str) -> dict:
        with self.db.connect() as connection:
            current = connection.execute(
                "SELECT * FROM jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
            if current is None:
                raise KeyError(f"Job {job_id} not found")
            if current["status"] == "published":
                raise ValueError("Published jobs cannot be modified")
            connection.execute(
                """
                UPDATE jobs
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, utc_now(), job_id),
            )
            return self.get_job(job_id, connection)

    def delete_job(self, job_id: int) -> None:
        with self.db.connect() as connection:
            current = connection.execute(
                "SELECT status FROM jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
            if current is None:
                raise KeyError(f"Job {job_id} not found")
            if current["status"] == "published":
                raise ValueError("Published jobs cannot be deleted")
            connection.execute("DELETE FROM jobs WHERE id = ?", (job_id,))

    def publish_now(self, payload: PublishRequest) -> dict[str, str]:
        publishing_limit = self.get_publishing_limit()
        if publishing_limit.usage is not None and publishing_limit.usage >= publishing_limit.limit:
            raise MetaApiError(
                f"Publishing limit reached: {publishing_limit.usage}/{publishing_limit.limit}"
            )
        return self._publish_media(
            media_url=payload.video_url,
            media_type=payload.media_type,
            caption=normalize_caption(payload.media_type, payload.caption),
            trial_params=payload.trial_params.model_dump() if payload.trial_params else None,
        )

    def get_publishing_limit(self) -> PublishingLimitResponse:
        raw = self.meta_client.get_content_publishing_limit()
        usage = self._extract_limit_usage(raw)
        return PublishingLimitResponse(
            limit=self.settings.meta_publish_limit,
            usage=usage,
            raw=raw,
        )

    def get_recent_instagram_post_metrics(self, *, force_refresh: bool = False, limit: int = 12) -> dict[str, Any]:
        with self._instagram_metrics_lock:
            cache_is_fresh = (
                self._instagram_metrics_cache is not None
                and (time.monotonic() - self._instagram_metrics_cached_at) < self._instagram_metrics_ttl_seconds
            )
            if cache_is_fresh and not force_refresh:
                return {
                    "fetched_at": self._instagram_metrics_cache["fetched_at"],
                    "cached": True,
                    "posts": self._instagram_metrics_cache["posts"],
                }

            posts = self._fetch_recent_instagram_post_metrics(limit=limit)
            fetched_at = utc_now()
            self._instagram_metrics_cache = {
                "fetched_at": fetched_at,
                "posts": posts,
            }
            self._instagram_metrics_cached_at = time.monotonic()
            return {
                "fetched_at": fetched_at,
                "cached": False,
                "posts": posts,
            }

    def run_due_jobs(self) -> int:
        if not self._lock.acquire(blocking=False):
            return 0

        processed = 0
        try:
            due_jobs = self._fetch_due_jobs()
            for job in due_jobs:
                processed += 1
                if not self._process_job(job):
                    break
        finally:
            self._lock.release()
        return processed

    def scheduler_loop(self, interval_seconds: int) -> None:
        while True:
            self.run_due_jobs()
            time.sleep(interval_seconds)

    def _fetch_due_jobs(self) -> list[dict]:
        due_cutoff = (datetime.now(UTC) + timedelta(seconds=self.settings.scheduler_lead_seconds)).isoformat()
        with self.db.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM jobs
                WHERE status = 'scheduled' AND publish_at <= ?
                ORDER BY publish_at ASC, id ASC
                """,
                (due_cutoff,),
            ).fetchall()
            return [dict(row) for row in rows]

    def _fetch_recent_instagram_post_metrics(self, *, limit: int) -> list[dict[str, Any]]:
        media_items = self.meta_client.list_recent_media(limit=limit)
        posts: list[dict[str, Any]] = []
        for item in media_items:
            media_id = str(item.get("id", "")).strip()
            if not media_id:
                continue

            details = self.meta_client.get_media_details(media_id)
            metrics = self._fetch_supported_media_insights(details)
            posts.append(
                {
                    "id": media_id,
                    "caption": details.get("caption"),
                    "media_type": details.get("media_type") or item.get("media_type") or "",
                    "media_product_type": details.get("media_product_type") or item.get("media_product_type"),
                    "permalink": details.get("permalink") or item.get("permalink"),
                    "timestamp": details.get("timestamp") or item.get("timestamp"),
                    "like_count": details.get("like_count", item.get("like_count")),
                    "comments_count": details.get("comments_count", item.get("comments_count")),
                    "views": metrics.get("views"),
                    "reach": metrics.get("reach"),
                    "saved": metrics.get("saved"),
                    "shares": metrics.get("shares"),
                    "total_interactions": metrics.get("total_interactions"),
                }
            )
        return posts

    def _fetch_supported_media_insights(self, media: dict[str, Any]) -> dict[str, Any]:
        media_id = str(media.get("id", "")).strip()
        if not media_id:
            return {}

        media_product_type = str(media.get("media_product_type") or "").upper()
        metric_sets: list[list[str]]
        if media_product_type == "REELS":
            metric_sets = [
                ["views", "reach", "saved", "shares", "total_interactions"],
                ["reach", "saved", "shares", "total_interactions"],
            ]
        else:
            metric_sets = [
                ["reach", "saved", "shares", "total_interactions"],
                ["reach", "saved"],
            ]

        for metrics in metric_sets:
            try:
                return self.meta_client.get_media_insights(media_id, metrics)
            except MetaApiError:
                continue
        return {}

    def _process_job(self, job: dict) -> bool:
        self._mark_status(job["id"], "processing", last_error=None)
        try:
            publishing_limit = self.get_publishing_limit()
            if publishing_limit.usage is not None and publishing_limit.usage >= publishing_limit.limit:
                raise MetaApiError(
                    f"Publishing limit reached: {publishing_limit.usage}/{publishing_limit.limit}"
                )
            result = self._publish_media(
                media_url=job["video_url"],
                media_type=job.get("media_type", "REEL"),
                caption=normalize_caption(job.get("media_type", "REEL"), job["caption"]),
                trial_params=(
                    {"graduation_strategy": job["trial_graduation_strategy"]}
                    if job["trial_graduation_strategy"]
                    else None
                ),
            )
        except Exception as exc:
            self._mark_status(job["id"], "failed", last_error=str(exc))
            return self._replace_failed_job(job)

        with self.db.connect() as connection:
            connection.execute(
                """
                UPDATE jobs
                SET status = ?, meta_creation_id = ?, meta_media_id = ?, last_error = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    "published",
                    result["creation_id"],
                    result["media_id"],
                    None,
                    utc_now(),
                    job["id"],
                ),
            )
        return True

    def _mark_status(self, job_id: int, status: str, last_error: str | None) -> None:
        with self.db.connect() as connection:
            connection.execute(
                """
                UPDATE jobs
                SET status = ?, last_error = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, last_error, utc_now(), job_id),
            )

    def _replace_failed_job(self, failed_job: dict) -> bool:
        with self.db.connect() as connection:
            replacement = connection.execute(
                """
                SELECT * FROM jobs
                WHERE status = 'scheduled' AND media_type = ?
                ORDER BY publish_at ASC, id ASC
                LIMIT 1
                """,
                (failed_job.get("media_type", "REEL"),),
            ).fetchone()
            if replacement is None:
                return False

            connection.execute(
                """
                UPDATE jobs
                SET publish_at = ?, replacement_for_job_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    failed_job["publish_at"],
                    failed_job["id"],
                    utc_now(),
                    replacement["id"],
                ),
            )
            promoted = connection.execute(
                "SELECT * FROM jobs WHERE id = ?",
                (replacement["id"],),
            ).fetchone()

        return self._process_job(dict(promoted)) if promoted is not None else False

    def _publish_media(
        self,
        *,
        media_url: str,
        media_type: str,
        caption: str,
        trial_params: dict[str, str] | None,
    ) -> dict[str, str]:
        caption = normalize_caption(media_type, caption)
        if media_type == "POST":
            stable_url = self._ensure_stable_post_url(media_url)
            return self.meta_client.publish_post(
                image_url=stable_url,
                caption=caption,
            )

        return self.meta_client.publish_reel(
            video_url=media_url,
            caption=caption,
            trial_params=trial_params,
        )

    @staticmethod
    def _extract_limit_usage(raw: dict) -> int | None:
        if isinstance(raw.get("quota_usage"), int):
            return raw["quota_usage"]
        data = raw.get("data")
        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, dict) and isinstance(first.get("quota_usage"), int):
                return first["quota_usage"]
        return None

    def _ensure_stable_post_url(self, image_url: str, *, force_restage: bool = False) -> str:
        final_url, content_type, body = self._download_media(image_url)
        if not body:
            raise MetaApiError(f"Post image URL returned empty body: {image_url}")
        if not (content_type or "").lower().startswith("image/"):
            raise MetaApiError(
                f"Post image URL did not return an image content type: {image_url} ({content_type or 'unknown'})"
            )
        if not force_restage and self._looks_stable_media_url(final_url):
            return final_url
        filename = self._filename_from_url(final_url)
        return self._upload_to_catbox(body, filename)

    @staticmethod
    def _looks_stable_media_url(url: str) -> bool:
        host = urllib.parse.urlparse(url).netloc.lower()
        return host.endswith("tmpfiles.org") or host.endswith("files.catbox.moe")

    @staticmethod
    def _filename_from_url(url: str) -> str:
        path = urllib.parse.urlparse(url).path
        name = os.path.basename(path) or "post_image.png"
        return name if "." in name else f"{name}.png"

    def _download_media(self, url: str) -> tuple[str, str, bytes]:
        with tempfile.NamedTemporaryFile(delete=False) as body_file:
            body_path = body_file.name
        try:
            result = subprocess.run(
                [
                    "curl",
                    "-fsSL",
                    "--max-time",
                    "60",
                    "-A",
                    "Meta-Uploader/1.0",
                    "-H",
                    "Accept: image/*,*/*;q=0.8",
                    "-o",
                    body_path,
                    "-w",
                    "%{content_type}\n%{url_effective}",
                    url,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            lines = result.stdout.strip().splitlines()
            content_type = lines[0].split(";", 1)[0].strip() if lines else ""
            final_url = lines[1].strip() if len(lines) > 1 else url
            with open(body_path, "rb") as handle:
                body = handle.read()
            detected = self._detect_image_content_type(body)
            return final_url, content_type or detected, body
        except subprocess.CalledProcessError as exc:
            error_text = (exc.stderr or exc.stdout or "").strip()
            raise MetaApiError(f"Failed to fetch post media URL {url}: {error_text}") from exc
        finally:
            try:
                os.unlink(body_path)
            except OSError:
                pass

    def _upload_to_catbox(self, content: bytes, filename: str) -> str:
        suffix = os.path.splitext(filename)[1] or ".png"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            result = subprocess.run(
                [
                    "curl",
                    "-fsS",
                    "--max-time",
                    "120",
                    "-F",
                    "reqtype=fileupload",
                    "-F",
                    f"fileToUpload=@{tmp_path};filename={filename}",
                    "https://catbox.moe/user/api.php",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            raw_url = result.stdout.strip()
        except subprocess.CalledProcessError as exc:
            error_text = (exc.stderr or exc.stdout or "").strip()
            raise MetaApiError(f"Failed to upload post media to catbox: {error_text}") from exc
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        if not raw_url.startswith("https://files.catbox.moe/"):
            raise MetaApiError(f"Unexpected catbox response: {raw_url}")
        final_url, content_type, body = self._download_media(raw_url)
        if len(body) == 0 or not (content_type or "").lower().startswith("image/"):
            raise MetaApiError(f"Catbox URL validation failed: {raw_url}")
        return final_url

    @staticmethod
    def _detect_image_content_type(content: bytes) -> str:
        if content.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if content.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
            return "image/webp"
        return ""
