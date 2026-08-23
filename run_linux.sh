#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then
  ./scripts/install_unix.sh
fi
exec .venv/bin/python app.py
