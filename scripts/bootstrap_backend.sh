#!/usr/bin/env bash
set -euo pipefail

cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest -q
