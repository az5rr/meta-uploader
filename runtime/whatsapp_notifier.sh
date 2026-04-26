#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

export PATH="$HOME/.local/bin:$PATH"
cd "$PROJECT_ROOT"

exec node "$PROJECT_ROOT/runtime/whatsapp_notifier.mjs" "$@"
