# Deployment

## Local service model

The repository ships with user-service examples in `deploy/`.
They assume:

- the project lives at `%h/Meta-Uploader`
- a local virtual environment exists at `.venv`
- the current user owns the project files

## Recommended production pattern

1. Create a dedicated Unix user for the service.
2. Clone the repo into that user’s home directory.
3. Create `.env` with production credentials.
4. Run `make install`.
5. Install the systemd user units.
6. Enable lingering for the service user if you need startup without login.

## Logging

With user services, inspect logs using:

```bash
journalctl --user -u meta-uploader.service -f
journalctl --user -u whatsapp-notifier.service -f
```

## Database

The default database is a local SQLite file:

- `meta_uploader.db`

For single-host operation this is fine.
For multi-host or HA operation, you would need a different persistence model.

## Backups

At minimum, back up:

- `.env`
- `meta_uploader.db`
- any external media source inventory you depend on

Do not back up and restore browser sessions blindly across unrelated machines.

## Security considerations

- keep Meta access tokens out of shell history when possible
- restrict filesystem permissions on `.env`
- do not expose the API publicly without authentication or a trusted network boundary
- do not commit runtime browser state
