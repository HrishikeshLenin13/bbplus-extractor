#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "Setting up BBPlus Local Viewer..."

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required."
  exit 1
fi

python3 -m venv .venv
source .venv/bin/activate

python3 -m pip install -r requirements.txt

echo ""
echo "Starting local viewer..."
echo "Open http://localhost:8000/output/viewer.html"
echo ""

python3 -m http.server 8000
