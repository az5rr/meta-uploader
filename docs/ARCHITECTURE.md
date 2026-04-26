# Architecture

## Overview

Meta-Uploader is split into four layers:

1. API layer
   - `app/main.py`
   - exposes HTTP endpoints for job creation, manual jobs, publishing, and health checks
2. Service layer
   - `app/service.py`
   - owns scheduling, caption normalization, job lifecycle, replacement logic, and publish orchestration
3. Persistence layer
   - `app/db.py`
   - manages SQLite schema creation and connections
4. External integrations
   - `app/meta_api.py`
   - Meta Graph API interaction
   - `runtime/whatsapp_notifier.mjs`
   - WhatsApp Web automation via Playwright

## Runtime flow

### Scheduled publish flow

1. A client submits `POST /jobs`.
2. The API validates payload shape in `app/schemas.py`.
3. `JobService.create_job()` stores the job in SQLite.
4. The scheduler thread started by FastAPI polls for due jobs.
5. For each due job:
   - publishing limits are checked
   - a Meta media container is created
   - the service polls until the container is ready
   - the media is published
6. The job record is updated to `published` or `failed`.

### Manual job flow

1. A client submits `POST /manual-jobs`.
2. The job is stored in `manual_jobs`.
3. An operator runs `manual_browser_assist.py`.
4. The script resolves the next pending job and launches the external browser-assist workflow.
5. The operator marks completion through `PATCH /manual-jobs/{id}`.

### WhatsApp notifier flow

1. `runtime/whatsapp_notifier.mjs` opens a persistent Chromium context.
2. It watches a target chat for commands and supported links.
3. It queries the local API and can schedule additional reel jobs through the helper script.
4. It emits notifications for successes and failures.

## Data model

### `jobs`

- scheduled Meta-publishable work
- stores publish time, caption, media type, status, Meta IDs, and failure details

### `manual_jobs`

- tracks jobs that require human completion in Meta Business Suite
- stores video path, desired publish time, browser command, and manual status

## Configuration model

Configuration is environment-driven:

- Meta credentials and publish behavior come from `.env`
- WhatsApp behavior is optional and also environment-driven
- service examples in `deploy/` assume a user-level systemd deployment

## Operational boundaries

This project does not include:

- secret management
- cloud infrastructure provisioning
- hosted object storage
- full OAuth setup automation

Those are deployment responsibilities documented in `docs/BUILD.md` and `docs/DEPLOYMENT.md`.
