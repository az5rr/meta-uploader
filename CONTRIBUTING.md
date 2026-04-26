# Contributing

## Development setup

```bash
make install
cp .env.example .env
```

If you need the WhatsApp notifier:

```bash
make install-whatsapp
```

## Local workflow

Run the API:

```bash
make run-dev
```

Run tests:

```bash
make test
```

## Pull request guidance

- Keep secrets, browser sessions, generated media, and databases out of Git.
- Prefer small, reviewable changes.
- Update the relevant docs when behavior or setup changes.
- If you change API behavior, update `docs/API.md`.
- If you change runtime or deploy behavior, update `docs/DEPLOYMENT.md`.
