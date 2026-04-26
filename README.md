# Meta-Uploader

Meta-Uploader is a small Instagram publishing stack built around the Meta Graph API.
It combines:

- a FastAPI service for scheduling and publishing reels/posts
- a SQLite-backed queue
- optional WhatsApp Web command handling
- an Arabic post generator used for feed assets

## Project layout

- `app/`: API, scheduling, publish logic, database access
- `bin/`: helper scripts for staging and queue creation
- `runtime/`: operational helpers and WhatsApp automation scripts
- `arabic_post_generator/`: post image generator
- `deploy/`: example systemd user units

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then fill `.env` with your own Meta credentials and optional WhatsApp settings.

## Full setup

See [SETUP.md](./SETUP.md) for a publishable installation guide that covers:

- Meta API prerequisites
- environment variables
- local development
- WhatsApp notifier setup
- optional systemd services

Before running the project, also read [NEW_USER_CHECKLIST.md](./NEW_USER_CHECKLIST.md) for the account-specific items every new operator must supply.

## API examples

Create a scheduled reel:

```bash
curl -X POST http://127.0.0.1:8000/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "video_url": "https://example.com/reel.mp4",
    "caption": "Scheduled reel",
    "trial_params": {
      "graduation_strategy": "MANUAL"
    },
    "publish_at": "2026-04-03T18:30:00Z"
  }'
```

Publish immediately:

```bash
curl -X POST http://127.0.0.1:8000/publish-now \
  -H 'Content-Type: application/json' \
  -d '{
    "video_url": "https://example.com/reel.mp4",
    "caption": "Immediate reel publish",
    "trial_params": {
      "graduation_strategy": "MANUAL"
    }
  }'
```

Queue a manual browser-assist job:

```bash
curl -X POST http://127.0.0.1:8000/manual-jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "video_path": "./inbox/example.mp4",
    "caption": "Queued reel for manual completion",
    "publish_at": "2026-04-06T05:00:00Z"
  }'
```

## Notes

- Meta must be able to fetch the public `video_url`.
- Scheduled jobs only publish while the service is running.
- The repository intentionally excludes live tokens, session state, databases, and generated media.
