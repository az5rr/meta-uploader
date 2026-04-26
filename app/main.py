from __future__ import annotations

import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.config import get_settings
from app.db import Database
from app.meta_api import MetaApiClient, MetaApiError
from app.schemas import (
    InstagramRecentPostsResponse,
    JobResponse,
    JobUpdate,
    ManualJobCreate,
    ManualJobResponse,
    ManualJobUpdate,
    PublishRequest,
    PublishResult,
    PublishingLimitResponse,
    ScheduledJobCreate,
)
from app.service import JobService

settings = get_settings()
database = Database(settings.database_path)
meta_client = MetaApiClient(settings)
job_service = JobService(database, meta_client, settings)


@asynccontextmanager
async def lifespan(_: FastAPI):
    scheduler_thread = threading.Thread(
        target=job_service.scheduler_loop,
        args=(settings.scheduler_interval_seconds,),
        daemon=True,
        name="meta-uploader-scheduler",
    )
    scheduler_thread.start()
    yield


app = FastAPI(title="Meta-Uploader", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/jobs", response_model=list[JobResponse])
def list_jobs() -> list[dict]:
    return job_service.list_jobs()


@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int) -> dict:
    try:
        return job_service.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.patch("/jobs/{job_id}", response_model=JobResponse)
def update_job(job_id: int, payload: JobUpdate) -> dict:
    try:
        return job_service.update_job(job_id, status=payload.status)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.delete("/jobs/{job_id}")
def delete_job(job_id: int) -> dict[str, bool]:
    try:
        job_service.delete_job(job_id)
        return {"deleted": True}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/manual-jobs", response_model=list[ManualJobResponse])
def list_manual_jobs() -> list[dict]:
    return job_service.list_manual_jobs()


@app.post("/manual-jobs", response_model=ManualJobResponse)
def create_manual_job(payload: ManualJobCreate) -> dict:
    return job_service.create_manual_job(payload)


@app.get("/manual-jobs/next", response_model=ManualJobResponse | None)
def next_manual_job() -> dict | None:
    return job_service.next_manual_job()


@app.patch("/manual-jobs/{job_id}", response_model=ManualJobResponse)
def update_manual_job(job_id: int, payload: ManualJobUpdate) -> dict:
    try:
        return job_service.update_manual_job(
            job_id,
            status=payload.status,
            last_error=payload.last_error,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/jobs", response_model=JobResponse)
def create_job(payload: ScheduledJobCreate) -> dict:
    return job_service.create_job(payload)


@app.post("/publish-now", response_model=PublishResult)
def publish_now(payload: PublishRequest) -> dict[str, str]:
    try:
        return job_service.publish_now(payload)
    except MetaApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/publishing-limit", response_model=PublishingLimitResponse)
def publishing_limit() -> PublishingLimitResponse:
    try:
        return job_service.get_publishing_limit()
    except MetaApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/instagram/recent-posts", response_model=InstagramRecentPostsResponse)
def instagram_recent_posts(refresh: bool = False, limit: int = 12) -> dict:
    try:
        bounded_limit = max(1, min(limit, 25))
        return job_service.get_recent_instagram_post_metrics(
            force_refresh=refresh,
            limit=bounded_limit,
        )
    except MetaApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/jobs/run")
def run_jobs() -> dict[str, int]:
    return {"processed": job_service.run_due_jobs()}
