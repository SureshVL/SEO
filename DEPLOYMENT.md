# OMNI-RANK — Go-Live Checklist (omnirank.io)

The full sequence from localhost to production. Do the steps in order —
each one unblocks the next. Expected total time: ~2–3 hours.

## 0. Prerequisites (done ✅)
- Domain **omnirank.io** purchased
- Supabase project live, migrations 001 + 002 applied (003 pending — step 6)
- Repo pushed to GitHub

## 1. Backend → Railway (~30 min)
1. https://railway.app → New Project → **Deploy from GitHub repo** → pick this repo.
2. Service settings → **Root Directory: `backend`** (it will build the Dockerfile).
3. Add a **Redis** database to the project (New → Database → Redis). Copy its
   `REDIS_URL` variable reference into the backend service.
4. Backend service → Variables → paste (values from your local `backend/.env`
   unless noted):

   ```
   ENVIRONMENT=production
   ORCHESTRATOR_API_KEY=<generate a strong random key — NOT the dev one>
   JWT_SECRET=<generate a strong random secret>
   SECRET_ENCRYPTION_KEY=<python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
   CORS_ORIGINS=https://omnirank.io,https://www.omnirank.io
   FRONTEND_URL=https://omnirank.io

   SUPABASE_URL=...
   SUPABASE_SERVICE_ROLE_KEY=...
   SUPABASE_ANON_KEY=...
   SUPABASE_JWT_SECRET=...

   GEMINI_API_KEY=...            (and GEMINI_API_KEYS if using multiple)
   GROQ_API_KEY=...              (optional but recommended — activates failover)
   SERPER_API_KEY=...
   FIRECRAWL_API_KEY=...
   PAGESPEED_API_KEY=...
   DATAFORSEO_LOGIN=...
   DATAFORSEO_PASSWORD=...

   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   GOOGLE_REDIRECT_URI=https://omnirank.io/dashboard/settings

   WHATSAPP_ACCESS_TOKEN=...     (from Meta developer portal)
   WHATSAPP_PHONE_NUMBER_ID=...
   WHATSAPP_VERIFY_TOKEN=<any secret you invent>
   WHATSAPP_APP_SECRET=...

   REDIS_URL=${{Redis.REDIS_URL}}
   ```
5. Settings → Networking → **Generate Domain** first (verify /health works on
   the railway.app URL), then **Custom Domain: `api.omnirank.io`** — Railway
   shows a CNAME target; add it in DNS (step 3).

## 2. Frontend → Vercel (~20 min)
1. https://vercel.com → Add New Project → import the repo.
2. **Root Directory: `frontend`** (framework auto-detected: Next.js).
3. Environment variables:

   ```
   NEXT_PUBLIC_API_URL=https://api.omnirank.io
   NEXT_PUBLIC_SITE_URL=https://omnirank.io
   NEXT_PUBLIC_SUPABASE_URL=...
   NEXT_PUBLIC_SUPABASE_ANON_KEY=...
   ```
4. Deploy. Then Settings → Domains → add **omnirank.io** (and www) — Vercel
   shows the DNS records to create.

## 3. DNS (at your registrar, ~10 min + propagation)
| Record | Host | Value |
|---|---|---|
| A | @ | 76.76.21.21 (Vercel — confirm the value Vercel shows) |
| CNAME | www | cname.vercel-dns.com |
| CNAME | api | <target Railway shows> |

## 4. Supabase auth URLs (~5 min)
Dashboard → Authentication → URL Configuration:
- **Site URL:** `https://omnirank.io`
- **Redirect URLs:** add `https://omnirank.io/**`
(Signup/confirmation emails now land on the live site.)

## 5. Google OAuth (~5 min)
Google Cloud Console → the OMNI-RANK OAuth client → Authorized redirect URIs →
add `https://omnirank.io/dashboard/settings`. Keep the localhost one for dev.
Also rotate the client secret (it appeared in a screenshot) — Add secret,
update Railway var, delete the old one.

## 6. Supabase migration 003 (~1 min)
SQL Editor → run `backend/migrations/003_whatsapp_links.sql`.

## 7. WhatsApp webhook (~10 min)
Meta developer portal → WhatsApp → Configuration → Webhook:
- Callback URL: `https://api.omnirank.io/webhooks/whatsapp`
- Verify token: the `WHATSAPP_VERIFY_TOKEN` you set in Railway
- Subscribe to the **messages** field.

## 8. Live smoke test (~15 min)
1. `https://api.omnirank.io/health` → `{"status":"ok"}`
2. Sign up with a fresh email on https://omnirank.io → confirmation email →
   lands back on omnirank.io.
3. Create project → add keywords → run AI Research → run Technical Audit.
4. Open the Copilot → "check my rankings" → completes.
5. Settings → connect GA4 + GSC (OAuth now redirects to the live domain).
6. Settings → WhatsApp Copilot → Generate code → text `LINK <code>` to the
   bot number → ask it something.
7. Landing page → pricing → lead-capture flow.

## 9. After go-live
- Point Resend/marketing links at omnirank.io.
- Watch Railway logs for the first day (`railway logs`).
- Set up UptimeRobot (free) on /health.
- When the first customer pays: Vercel Pro + Supabase Pro upgrades.
