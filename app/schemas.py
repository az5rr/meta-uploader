from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator

MediaType = Literal["REEL", "POST"]


class TrialParams(BaseModel):
    graduation_strategy: str = Field(pattern="^(MANUAL|SS_PERFORMANCE)$")


class PublishRequest(BaseModel):
    video_url: str = Field(min_length=1)
    caption: str = Field(min_length=1, max_length=2200)
    media_type: MediaType = "REEL"
    trial_params: TrialParams | None = None


class ScheduledJobCreate(PublishRequest):
    publish_at: datetime

    @field_validator("publish_at")
    @classmethod
    def validate_publish_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("publish_at must include a timezone")
        return value.astimezone(timezone.utc)


class JobResponse(BaseModel):
    id: int
    video_url: str
    caption: str
    media_type: MediaType = "REEL"
    trial_graduation_strategy: str | None = None
    publish_at: datetime
    status: str
    meta_creation_id: str | None = None
    meta_media_id: str | None = None
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime


class JobUpdate(BaseModel):
    status: str = Field(pattern="^(scheduled|cancelled)$")


class ManualJobCreate(BaseModel):
    video_path: str = Field(min_length=1)
    caption: str = Field(min_length=1, max_length=2200)
    publish_at: datetime

    @field_validator("publish_at")
    @classmethod
    def validate_publish_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("publish_at must include a timezone")
        return value


class ManualJobUpdate(BaseModel):
    status: str = Field(pattern="^(scheduled|opening|ready_for_manual_completion|completed|failed)$")
    last_error: str | None = None


class ManualJobResponse(BaseModel):
    id: int
    video_path: str
    caption: str
    publish_at: datetime
    status: str
    browser_command: str | None = None
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime


class PublishResult(BaseModel):
    creation_id: str
    media_id: str


class PublishingLimitResponse(BaseModel):
    limit: int
    usage: int | None = None
    raw: dict


class InstagramRecentPostMetricsResponse(BaseModel):
    id: str
    caption: str | None = None
    media_type: str
    media_product_type: str | None = None
    permalink: str | None = None
    timestamp: datetime | None = None
    like_count: int | None = None
    comments_count: int | None = None
    views: int | None = None
    reach: int | None = None
    saved: int | None = None
    shares: int | None = None
    total_interactions: int | None = None


class InstagramRecentPostsResponse(BaseModel):
    fetched_at: datetime
    cached: bool
    posts: list[InstagramRecentPostMetricsResponse]
