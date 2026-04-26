# Development

## Repository layout

```text
app/                     FastAPI application and core scheduler logic
arabic_post_generator/   Arabic asset generation subsystem
bin/                     helper scripts
deploy/                  systemd user service examples
docs/                    project documentation
runtime/                 WhatsApp automation runtime
```

## Python setup

```bash
make install
```

## Running locally

```bash
make run-dev
```

## Testing

```bash
make test
```

Current automated coverage is strongest in the Arabic post generator.
The API layer would benefit from dedicated endpoint tests in future iterations.

## Recommended next improvements

- add FastAPI endpoint tests
- add CI for lint and test runs
- add typed settings validation
- separate project-specific caption policy from generic publish logic
