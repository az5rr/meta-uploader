# Meta-Uploader

Meta-Uploader is an Instagram publishing stack built around the Meta Graph API.
It provides a scheduler-backed API for publishing reels and posts, plus optional
WhatsApp automation and an Arabic feed-post generator.

## Features

- FastAPI service for scheduling and immediate publishing
- SQLite-backed job queue
- Manual-job workflow for browser-assisted publishing
- Optional WhatsApp Web notifier and command handler
- Arabic feed-post generator subsystem

## Repository structure

- `app/`: API, scheduler, Meta integration, persistence access
- `arabic_post_generator/`: Arabic rendering subsystem
- `bin/`: helper scripts
- `runtime/`: WhatsApp runtime helpers
- `deploy/`: systemd user service examples
- `docs/`: architecture, API, build, deployment, and development guides

## Quick start

```bash
make install
cp .env.example .env
make run
```

Then fill `.env` with your own Meta credentials and optional WhatsApp settings.

## Documentation

- [SETUP.md](./SETUP.md)
- [NEW_USER_CHECKLIST.md](./NEW_USER_CHECKLIST.md)
- [docs/BUILD.md](./docs/BUILD.md)
- [docs/API.md](./docs/API.md)
- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)
- [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md)
- [docs/DEVELOPMENT.md](./docs/DEVELOPMENT.md)
- [CONTRIBUTING.md](./CONTRIBUTING.md)

## Core build path

If you want the full step-by-step build flow, start here:

1. Read [NEW_USER_CHECKLIST.md](./NEW_USER_CHECKLIST.md)
2. Follow [SETUP.md](./SETUP.md)
3. Use [docs/BUILD.md](./docs/BUILD.md) for the full operator build guide

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
