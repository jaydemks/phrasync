#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -f .venv/bin/activate ]]; then
  echo "Run install_unix.sh or install_core_unix.sh first." >&2
  exit 1
fi
source .venv/bin/activate
python -m pip install -r requirements-ai.txt
