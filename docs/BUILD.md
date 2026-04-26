# Build Guide

This guide is written for someone building the project from zero on a clean machine.

## 1. Understand what you are building

Meta-Uploader is not just a website or a CLI. It is a small operations stack:

- a FastAPI backend
- a SQLite job store
- a scheduler thread that publishes due jobs
- optional WhatsApp Web automation
- optional Arabic image generation for feed posts

Before you install anything, decide whether you need:

- only the API and scheduler
- API plus manual browser-assist jobs
- API plus WhatsApp notifier
- API plus Arabic post generator

If you only need scheduled publishing, you can ignore the WhatsApp section entirely.

## 2. System requirements

Minimum:

- Linux or macOS preferred
- Python `3.11+`
- Node.js `18+` for WhatsApp automation
- Chromium available through Playwright if using WhatsApp automation

Recommended:

- a dedicated non-root user for the service
- a persistent working directory
- systemd user services for long-running operation

## 3. Clone and bootstrap

```bash
git clone <your-repo-url> Meta-Uploader
cd Meta-Uploader
make install
cp .env.example .env
```

If you plan to use WhatsApp automation:

```bash
make install-whatsapp
```

## 4. Create your Meta credentials

You must supply your own:

- Instagram professional account
- Meta application
- access token
- Instagram user id

Required Meta permissions:

- `instagram_business_basic`
- `instagram_business_content_publish`

Set these in `.env`:

```dotenv
META_ACCESS_TOKEN=replace-me
META_IG_USER_ID=replace-me
META_GRAPH_VERSION=v24.0
META_POLL_SECONDS=60
META_PUBLISH_LIMIT=100
SCHEDULER_INTERVAL_SECONDS=30
SCHEDULER_LEAD_SECONDS=30
DATABASE_PATH=meta_uploader.db
```

If you do not know your Instagram user id:

```bash
curl "https://graph.instagram.com/me?fields=user_id,username&access_token=YOUR_TOKEN"
```

## 5. Start the API locally

```bash
make run-dev
```

Confirm service health:

```bash
curl http://127.0.0.1:8000/health
```

You should receive:

```json
{"status":"ok"}
```

## 6. Verify the scheduler works

The scheduler starts when FastAPI starts. You do not launch a separate worker.

To test the pipeline safely:

1. create a job with a future `publish_at`
2. list jobs with `GET /jobs`
3. force a run with `POST /jobs/run` if needed
4. inspect job state transitions

## 7. Build the WhatsApp notifier

This step is optional.

Add WhatsApp-related `.env` keys:

```dotenv
WHATSAPP_TARGET_PHONE=15551234567
WHATSAPP_CHECK_INTERVAL_SECONDS=10
WHATSAPP_REELS_LOW_THRESHOLD=3
WHATSAPP_STATUS_TIMEZONE=UTC
WHATSAPP_HEADLESS=true
```

Create the browser session:

```bash
./runtime/whatsapp_notifier.sh --login-only
```

This creates runtime-only session artifacts under:

- `runtime/whatsapp_session/`
- `runtime/whatsapp_output/`

These must never be committed.

## 8. Build the Arabic post generator

The Arabic renderer is a subcomponent in `arabic_post_generator/`.

It includes:

- rendering pipeline
- font loading
- review UI
- workflow helpers

Install its dependencies separately if you want to use it directly:

```bash
cd arabic_post_generator
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Run its tests:

```bash
pytest tests
```

## 9. Productionize the service

Example service files are already included:

- `deploy/meta-uploader.service`
- `deploy/whatsapp-notifier.service`

Install as user services:

```bash
mkdir -p ~/.config/systemd/user
cp deploy/meta-uploader.service ~/.config/systemd/user/
cp deploy/whatsapp-notifier.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now meta-uploader.service
systemctl --user enable --now whatsapp-notifier.service
```

## 10. Common mistakes

- using a private or temporary media URL that Meta cannot fetch
- forgetting timezone data in `publish_at`
- committing `.env`, browser sessions, or databases
- assuming the WhatsApp notifier works without a manual first login
- treating example scripts as universal production logic

## 11. What to customize before real use

You should review and possibly change:

- caption rules in `app/service.py`
- posting strategy
- media staging workflow
- manual browser-assist integration
- deployment supervision and logging
