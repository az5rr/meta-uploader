# WhatsApp Web Bot Setup

Files:

- `runtime/whatsapp_notifier.mjs`
- `runtime/whatsapp_notifier.sh`
- `deploy/whatsapp-notifier.service`
- `runtime/whatsapp_session/`
- `runtime/whatsapp_output/`

Required `.env` keys:

- `WHATSAPP_TARGET_PHONE`
- `WHATSAPP_CHECK_INTERVAL_SECONDS`
- `WHATSAPP_REELS_LOW_THRESHOLD`
- `WHATSAPP_STATUS_TIMEZONE`
- `WHATSAPP_HEADLESS`

Install runtime dependencies:

```bash
cd runtime
npm install
npx playwright install chromium
cd ..
```

One-time login check:

```bash
./runtime/whatsapp_notifier.sh --login-only
```

If login is required, the bot writes debug artifacts under `runtime/whatsapp_output/`.

Manual status bundle:

```bash
./runtime/whatsapp_notifier.sh --send-status
```

Enable as a user service:

```bash
mkdir -p ~/.config/systemd/user
cp deploy/whatsapp-notifier.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now whatsapp-notifier.service
```

Primary chat commands:

- `status`
- `jobs`
- `reel-links`
- `queue`
- `next-id`
- `last-upload`
- `today-report`
- `help`

Legacy aliases:

- `reel links` -> `reel-links`
- `need reels` -> `reel-links`
- `next` -> `next-id`
- `health` -> `status`

Operational note:

- `runtime/whatsapp_session/`, `runtime/whatsapp_output/`, and `runtime/whatsapp_notifier_state.json` are runtime-only and should not be committed.
