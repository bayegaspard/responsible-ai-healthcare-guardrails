#!/usr/bin/env bash
# Start the demo on macOS or Linux. Run from the repository root:  ./scripts/run.sh
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -d .venv ]; then echo "Run ./scripts/setup.sh first."; exit 1; fi
. .venv/bin/activate
python app/app.py
