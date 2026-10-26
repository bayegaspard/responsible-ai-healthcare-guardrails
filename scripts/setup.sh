#!/usr/bin/env bash
# One-time setup on macOS or Linux. Run from the repository root:  ./scripts/setup.sh
set -euo pipefail
cd "$(dirname "$0")/.."

PY=${PYTHON:-python3}
"$PY" -c 'import sys; assert sys.version_info >= (3, 10), "Python 3.10 or newer is required"'

echo "==> Creating virtual environment in .venv"
"$PY" -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip -q
echo "==> Installing Python packages"
pip install -r requirements.txt -q

if ! command -v ollama >/dev/null 2>&1; then
  echo "!! Ollama is not installed. Get it from https://ollama.com/download, then rerun this script."
  exit 1
fi
echo "==> Pulling models (about 10 GB the first time)"
ollama pull llama3
ollama pull llama3.1

echo "==> Running policy tests"
python -m unittest discover tests -q

echo "Setup complete. Start the demo with: ./scripts/run.sh"
