# Meta-Uploader System Overview

This repository contains an Instagram automation stack with four main parts:

- `app/`: FastAPI application, scheduler, Meta API integration, database access
- `runtime/`: automation helpers, WhatsApp notifier, temporary runtime files
- `arabic_post_generator/`: image generator for Arabic feed posts
- `deploy/`: example user-service definitions

Design rules:

- Treat `arabic_post_generator/` as part of the same project, not a separate product.
- Keep generated media and browser sessions out of version control.
- Feed posts default to Arabic-only images unless a different brief is required.
