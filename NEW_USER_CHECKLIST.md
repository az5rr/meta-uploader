# New User Checklist

This project is sanitized for publishing, but it is not plug-and-play until you add your own accounts, credentials, and runtime setup.

## What you need

- A machine with `Python 3.11+`
- `Node.js 18+` if you want the WhatsApp notifier
- An Instagram professional account
- A Meta app with:
  - `instagram_business_basic`
  - `instagram_business_content_publish`
- A valid Instagram user access token for your own account
- Your own Instagram user id
- Publicly reachable media URLs for reels you want Meta to publish

## Required `.env` values

You must create `.env` from `.env.example` and fill in your own values.

Required Meta settings:

- `META_ACCESS_TOKEN`
- `META_IG_USER_ID`

Common runtime settings:

- `META_GRAPH_VERSION`
- `META_POLL_SECONDS`
- `META_PUBLISH_LIMIT`
- `SCHEDULER_INTERVAL_SECONDS`
- `SCHEDULER_LEAD_SECONDS`
- `DATABASE_PATH`

Optional WhatsApp notifier settings:

- `WHATSAPP_TARGET_PHONE`
- `WHATSAPP_CHECK_INTERVAL_SECONDS`
- `WHATSAPP_REELS_LOW_THRESHOLD`
- `WHATSAPP_STATUS_TIMEZONE`
- `WHATSAPP_HEADLESS`

## If you want WhatsApp control

You also need:

- your own WhatsApp Web login
- a local Playwright/Chromium installation
- a one-time login session created by running:

```bash
./runtime/whatsapp_notifier.sh --login-only
```

Do not commit:

- `runtime/whatsapp_session/`
- `runtime/whatsapp_output/`
- `.env`
- `meta_uploader.db`

## If you want manual browser-assist jobs

`manual_browser_assist.py` can open an external helper script, but you must provide that script path yourself.

Set:

```bash
export META_BROWSER_ASSIST_SCRIPT=/path/to/your/browser_assist_script.py
```

## Project-specific decisions you must make

Before using this in production, decide and update:

- your caption policy
- your posting schedule
- your hashtags
- your timezone
- your media hosting/staging workflow
- whether you want to use the Arabic post generator

Some helper scripts in `runtime/` are examples from one deployment and may need adjustment for your own content plan.

## Recommended reading order

1. `README.md`
2. `SETUP.md`
3. `WHATSAPP_SETUP.md`
4. `SYSTEM_OVERVIEW.md`

## Summary

This repository provides the application code and examples.
You must still connect it to your own Meta account, your own WhatsApp session, your own media workflow, and your own publishing strategy.
