#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then
  echo "Virtual environment not found. Create it with: python -m venv .venv" >&2
  echo "Then install: .venv/bin/python -m pip install -r requirements.txt" >&2
  exit 1
fi
exec .venv/bin/python -m streamlit run app.py
