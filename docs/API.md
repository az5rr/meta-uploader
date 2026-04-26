# API Reference

Base URL in local development:

```text
http://127.0.0.1:8000
```

## Health

### `GET /health`

Returns:

```json
{"status":"ok"}
```

## Scheduled jobs

### `GET /jobs`

List all scheduled and historical jobs ordered by publish time.

### `GET /jobs/{job_id}`

Fetch a single job.

### `POST /jobs`

Create a scheduled job.

Example:

```json
{
  "video_url": "https://example.com/reel.mp4",
  "caption": "My caption",
  "media_type": "REEL",
  "trial_params": {
    "graduation_strategy": "MANUAL"
  },
  "publish_at": "2026-05-01T18:30:00Z"
}
```

Notes:

- `publish_at` must include timezone information.
- `media_type` is `REEL` or `POST`.
- captions are normalized by the service layer before storage/publish.

### `PATCH /jobs/{job_id}`

Allowed status changes:

- `scheduled`
- `cancelled`

### `DELETE /jobs/{job_id}`

Deletes non-published jobs.

### `POST /jobs/run`

Forces a due-job processing pass immediately.

## Immediate publishing

### `POST /publish-now`

Publishes a job without storing it as a scheduled record.

Example:

```json
{
  "video_url": "https://example.com/reel.mp4",
  "caption": "Immediate publish",
  "media_type": "REEL"
}
```

## Manual jobs

### `GET /manual-jobs`

List manual jobs.

### `GET /manual-jobs/next`

Get the next scheduled manual job, if any.

### `POST /manual-jobs`

Create a manual job.

Example:

```json
{
  "video_path": "./inbox/example.mp4",
  "caption": "Finish this one manually",
  "publish_at": "2026-05-01T18:30:00Z"
}
```

### `PATCH /manual-jobs/{job_id}`

Allowed statuses:

- `scheduled`
- `opening`
- `ready_for_manual_completion`
- `completed`
- `failed`

## Meta utility endpoints

### `GET /publishing-limit`

Returns the configured limit and current usage data as reported by Meta.

### `GET /instagram/recent-posts`

Query params:

- `refresh`: force a fresh pull instead of using the short in-memory cache
- `limit`: bounded between `1` and `25`
