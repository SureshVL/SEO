# OMNI-RANK - one-command local launch for Windows (PowerShell).
#
#   ./scripts/dev-local.ps1
#
# First run creates backend/.env and frontend/.env.local from the templates,
# auto-generating the security secret the app needs to boot. It then installs
# dependencies and opens the backend and frontend each in its own window.
#
# Backend:  http://localhost:8000  (API docs at /docs)
# Frontend: http://localhost:3000
#
# Prerequisites: Python 3.11+ and Node 18+ on PATH.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Gen-Hex32 {
    $bytes = New-Object 'System.Byte[]' 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    ($bytes | ForEach-Object { $_.ToString('x2') }) -join ''
}
function Write-Utf8NoBom($path, $content) {
    [System.IO.File]::WriteAllText((Join-Path $root $path), $content, (New-Object System.Text.UTF8Encoding($false)))
}

# ---------- prerequisites ----------
$python = $null
foreach ($c in @('python', 'py')) {
    if (Get-Command $c -ErrorAction SilentlyContinue) { $python = $c; break }
}
if (-not $python) {
    Write-Host "Python not found. Install Python 3.11+ from https://www.python.org/downloads/ (check 'Add to PATH')." -ForegroundColor Red
    exit 1
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "npm not found. Install Node 18+ from https://nodejs.org/" -ForegroundColor Red
    exit 1
}

# ---------- collect Supabase (only if needed) ----------
$needFrontend = -not (Test-Path frontend/.env.local)
$needBackend = -not (Test-Path backend/.env)
$sbUrl = ""; $sbAnon = ""
if ($needFrontend -or $needBackend) {
    Write-Host "Enter your Supabase details (Project Settings > API). Leave blank to skip for now." -ForegroundColor Cyan
    $sbUrl = Read-Host "  NEXT_PUBLIC_SUPABASE_URL (https://xxxx.supabase.co)"
    $sbAnon = Read-Host "  NEXT_PUBLIC_SUPABASE_ANON_KEY (eyJ... public anon key)"
}

# ---------- backend/.env ----------
if ($needBackend) {
    Write-Host "-> Creating backend/.env (generating security secret)..."
    $t = Get-Content .env.example -Raw
    $orch = Gen-Hex32
    $t = $t -replace '(?m)^ORCHESTRATOR_API_KEY=.*$', "ORCHESTRATOR_API_KEY=$orch"
    if ($sbUrl)  { $t = $t -replace '(?m)^SUPABASE_URL=.*$',      "SUPABASE_URL=$sbUrl" }
    if ($sbAnon) { $t = $t -replace '(?m)^SUPABASE_ANON_KEY=.*$', "SUPABASE_ANON_KEY=$sbAnon" }
    Write-Utf8NoBom 'backend/.env' $t
    Write-Host "   backend/.env ready (strong ORCHESTRATOR_API_KEY set)" -ForegroundColor Green
}

# ---------- frontend/.env.local ----------
if ($needFrontend) {
    Write-Host "-> Creating frontend/.env.local..."
    $fe = "NEXT_PUBLIC_API_URL=http://localhost:8000`n" +
          "NEXT_PUBLIC_SUPABASE_URL=$sbUrl`n" +
          "NEXT_PUBLIC_SUPABASE_ANON_KEY=$sbAnon`n" +
          "NEXT_PUBLIC_APP_NAME=OMNI-RANK`n"
    Write-Utf8NoBom 'frontend/.env.local' $fe
    Write-Host "   frontend/.env.local ready" -ForegroundColor Green
}

# ---------- dependencies ----------
Write-Host "-> Installing backend deps (this can take a minute)..."
& $python -m pip install -q -e "backend/.[render]" 2>$null
if ($LASTEXITCODE -ne 0) { & $python -m pip install -q -e "backend/." }
& $python -m pip install -q cryptography 2>$null

Write-Host "-> Installing frontend deps..."
Push-Location frontend
npm install --silent
Pop-Location

# ---------- launch (each in its own window) ----------
Write-Host ""
Write-Host "=== Starting OMNI-RANK ===" -ForegroundColor Cyan
Write-Host "Backend:  http://localhost:8000  (docs: http://localhost:8000/docs)"
Write-Host "Frontend: http://localhost:3000"
Write-Host "Two new PowerShell windows will open. Close them to stop the servers."
Write-Host ""

$backendCmd = "Set-Location '$root\backend'; & $python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
Start-Process powershell -ArgumentList '-NoExit', '-Command', $backendCmd

$frontendCmd = "Set-Location '$root\frontend'; npm run dev"
Start-Process powershell -ArgumentList '-NoExit', '-Command', $frontendCmd

Write-Host "Launched. Give it ~15s, then open http://localhost:3000" -ForegroundColor Green
