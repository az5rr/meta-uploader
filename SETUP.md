# Setup Guide

This repository is safe to publish, but it does not include live credentials, browser sessions, media, or database state.

## Prerequisites

- Python `3.11+`
- Node.js `18+` if you want the WhatsApp notifier
- An Instagram professional account connected to Meta
- A Meta app with:
  - `instagram_business_basic`
  - `instagram_business_content_publish`
- A valid Instagram user access token

## 1. Clone and install

```bash
git clone <your-repo-url> Meta-Uploader
cd Meta-Uploader
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If you want the WhatsApp notifier:

```bash
cd runtime
npm install
npx playwright install chromium
cd ..
```

## 2. Configure environment variables

Copy the template and fill in your values:

```bash
cp .env.example .env
```

Required Meta keys:

- `META_ACCESS_TOKEN`
- `META_IG_USER_ID`

Common optional keys:

- `META_GRAPH_VERSION`
- `META_POLL_SECONDS`
- `META_PUBLISH_LIMIT`
- `SCHEDULER_INTERVAL_SECONDS`
- `SCHEDULER_LEAD_SECONDS`
- `DATABASE_PATH`

WhatsApp notifier keys:

- `WHATSAPP_TARGET_PHONE`
- `WHATSAPP_CHECK_INTERVAL_SECONDS`
- `WHATSAPP_REELS_LOW_THRESHOLD`
- `WHATSAPP_STATUS_TIMEZONE`
- `WHATSAPP_HEADLESS`

If you do not know your Instagram user id:

```bash
curl "https://graph.instagram.com/me?fields=user_id,username&access_token=YOUR_TOKEN"
```

## 3. Run the API

```bash
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Useful endpoints:

- `GET /jobs`
- `POST /jobs`
- `POST /publish-now`
- `GET /publishing-limit`
- `GET /manual-jobs`
- `POST /manual-jobs`

## 4. Optional: WhatsApp notifier

One-time login test:

```bash
./runtime/whatsapp_notifier.sh --login-only
```

Manual status send:

```bash
./runtime/whatsapp_notifier.sh --send-status
```

The notifier stores browser session data under `runtime/whatsapp_session/`. That directory is intentionally gitignored and should never be committed.

## 5. Optional: systemd user services

Example units are in `deploy/`.

Install them as user services:

```bash
mkdir -p ~/.config/systemd/user
cp deploy/meta-uploader.service ~/.config/systemd/user/
cp deploy/whatsapp-notifier.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now meta-uploader.service
systemctl --user enable --now whatsapp-notifier.service
```

## 6. Publishing workflow notes

- The API expects a public `video_url` for Meta-hosted publishing.
- Runtime helpers can temporarily stage local files before job creation.
- Generated media, database files, browser session state, and inbox assets are excluded from Git by default.
