#!/usr/bin/env bash
# OMNI-RANK — one-command local launch (backend + frontend on localhost).
#
#   ./scripts/dev-local.sh
#
# First run creates backend/.env and frontend/.env.local from the templates,
# auto-generating the security secrets the app requires to boot. Fill in your
# Supabase URL + anon key when prompted (or edit the env files afterwards).
#
# Backend:  http://localhost:8000  (API docs at /docs)
# Frontend: http://localhost:3000
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Resolve a Python command (Windows Git Bash usually has `python`, not `python3`).
if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else echo "Python not found. Install Python 3.11+ and re-run." >&2; exit 1; fi

gen() { "$PY" -c "import secrets;print(secrets.token_hex(32))"; }
gen_fernet() { "$PY" -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())" 2>/dev/null || echo ""; }

# ---------- backend/.env ----------
if [ ! -f backend/.env ]; then
  echo "→ Creating backend/.env (generating security secrets)…"
  cp .env.example backend/.env
  # Satisfy the boot guard with real secrets instead of the dev escape hatch.
  ORCH_KEY="$(gen)"
  ENC_KEY="$(gen_fernet)"
  # Portable in-place edits (works on both GNU and BSD sed).
  "$PY" - "$ORCH_KEY" "$ENC_KEY" <<'PY'
import sys, re, pathlib
orch, enc = sys.argv[1], sys.argv[2]
p = pathlib.Path("backend/.env"); t = p.read_text()
t = re.sub(r"^ORCHESTRATOR_API_KEY=.*$", f"ORCHESTRATOR_API_KEY={orch}", t, flags=re.M)
if "SECRET_ENCRYPTION_KEY=" in t:
    t = re.sub(r"^SECRET_ENCRYPTION_KEY=.*$", f"SECRET_ENCRYPTION_KEY={enc}", t, flags=re.M)
elif enc:
    t += f"\nSECRET_ENCRYPTION_KEY={enc}\n"
p.write_text(t)
PY
  echo "  ✓ backend/.env ready (strong ORCHESTRATOR_API_KEY + SECRET_ENCRYPTION_KEY set)"
  echo "  ⚠  Add your SUPABASE_URL / SUPABASE_ANON_KEY to backend/.env for user login."
fi

# ---------- frontend/.env.local ----------
if [ ! -f frontend/.env.local ]; then
  echo "→ Creating frontend/.env.local…"
  read -r -p "   NEXT_PUBLIC_SUPABASE_URL (https://xxxx.supabase.co): " SB_URL || true
  read -r -p "   NEXT_PUBLIC_SUPABASE_ANON_KEY (eyJ… public key): " SB_ANON || true
  cat > frontend/.env.local <<EOF
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=${SB_URL:-}
NEXT_PUBLIC_SUPABASE_ANON_KEY=${SB_ANON:-}
NEXT_PUBLIC_APP_NAME=OMNI-RANK
EOF
  echo "  ✓ frontend/.env.local ready"
fi

# ---------- dependencies ----------
echo "→ Installing backend deps…"
"$PY" -m pip install -q -e "backend/.[render]" 2>/dev/null \
  || "$PY" -m pip install -q -e "backend/." 2>/dev/null \
  || "$PY" -m pip install -q fastapi "uvicorn[standard]" pydantic pydantic-settings httpx requests python-dotenv
"$PY" -m pip install -q cryptography 2>/dev/null || true

echo "→ Installing frontend deps…"
( cd frontend && npm install --silent )

# ---------- launch ----------
echo ""
echo "=== Starting OMNI-RANK ==="
echo "Backend:  http://localhost:8000  (docs: http://localhost:8000/docs)"
echo "Frontend: http://localhost:3000"
echo "Press Ctrl-C to stop both."
echo ""

pids=()
cleanup() { echo; echo "Stopping…"; for p in "${pids[@]}"; do kill "$p" 2>/dev/null || true; done; }
trap cleanup INT TERM EXIT

( cd backend && set -a && . ./.env && set +a && \
  exec "$PY" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 ) &
pids+=($!)

( cd frontend && exec npm run dev ) &
pids+=($!)

wait
