# OMNI-RANK OR-1 — Deployment Guide

## Prerequisites

- Supabase project (free tier works for dev)
- Anthropic API key (Claude Sonnet access)
- Serper API key (serper.dev)
- Firecrawl API key (firecrawl.dev)
- Razorpay account (for billing — optional for MVP)
- Resend account (for emails — optional for MVP)

## 1. Supabase Setup

```bash
# Install Supabase CLI
npm i -g supabase

# Link to your project
supabase link --project-ref YOUR_PROJECT_REF

# Run migrations
supabase db push
```

This creates all 17 tables, RLS policies, triggers, and indexes.

**Enable Google OAuth:**
1. Go to Supabase Dashboard → Authentication → Providers
2. Enable Google provider
3. Add your Google OAuth client ID and secret
4. Set redirect URL to `https://yourdomain.com/auth/callback`

## 2. Local Development

```bash
# Copy environment template
cp .env.example .env
# Fill in all keys

# Start everything
docker compose up

# Access:
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# API docs: http://localhost:8000/docs
```

## 3. Deploy to Railway

### Backend

```bash
# From project root
railway init
railway link

# Set environment variables
railway variables set ENVIRONMENT=prod
railway variables set ANTHROPIC_API_KEY=sk-ant-...
railway variables set SERPER_API_KEY=...
railway variables set FIRECRAWL_API_KEY=...
railway variables set SUPABASE_URL=https://xxx.supabase.co
railway variables set SUPABASE_SERVICE_ROLE_KEY=...
railway variables set ORCHESTRATOR_API_KEY=<generate-a-strong-key>
railway variables set REDIS_URL=<from-railway-redis>
railway variables set CORS_ORIGINS=https://yourdomain.com

# Deploy
railway up --service backend
```

### Frontend (Vercel)

```bash
cd frontend
vercel --prod

# Set environment variables in Vercel dashboard:
# NEXT_PUBLIC_API_URL=https://your-railway-backend.up.railway.app
# NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
# NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
```

### Redis (Railway)

Add a Redis service in Railway dashboard. Copy the `REDIS_URL` to your backend service variables.

## 4. Deploy to Render (Alternative)

Create `render.yaml` in project root (already included):

```bash
# Deploy both services
render deploy
```

## 5. Daily Rank Tracking Cron

### Option A: Railway Cron
Add a cron job in Railway that runs:
```bash
python -m app.cron
```
Schedule: `0 6 * * *` (6 AM UTC daily)

### Option B: GitHub Actions Cron
Already configured in `.github/workflows/ci.yml`. Add a cron workflow:
```yaml
on:
  schedule:
    - cron: '0 6 * * *'
```

## 6. Razorpay Setup (Billing)

1. Create Razorpay account at razorpay.com
2. Create subscription plans matching your tiers:
   - Starter: ₹1,999/mo
   - Growth: ₹4,999/mo
   - Agency: ₹14,999/mo
3. Copy plan IDs to your backend config or database
4. Set webhook URL: `https://your-backend.com/webhooks/razorpay`
5. Set environment variables:
   ```
   RAZORPAY_KEY_ID=rzp_live_...
   RAZORPAY_KEY_SECRET=...
   RAZORPAY_WEBHOOK_SECRET=...
   ```

## 7. Domain & SSL

- Point your domain to Vercel (frontend)
- Backend gets SSL automatically from Railway/Render
- Update `CORS_ORIGINS` to include your production domain

## 8. Monitoring

### Health Check
```bash
curl https://your-backend.com/health
# {"status":"ok","service":"OMNI-RANK OR-1","ai":"enabled"}
```

### Recommended Tools
- **Uptime**: UptimeRobot (free) — monitor `/health`
- **Errors**: Sentry (free tier) — add `sentry-sdk[fastapi]` to backend
- **Logs**: Railway/Render built-in log viewer
- **Analytics**: Plausible or PostHog (privacy-friendly)

## 9. Security Checklist

- [ ] Change default `ORCHESTRATOR_API_KEY` from `dev-orchestrator-key`
- [ ] Set strong `JWT_SECRET`
- [ ] Enable Supabase RLS (already configured in migrations)
- [ ] Set `ENVIRONMENT=prod` (prevents startup with default keys)
- [ ] Configure CORS to only allow your frontend domain
- [ ] Enable Supabase email confirmation
- [ ] Set up Razorpay webhook signature verification
- [ ] Review rate limiting settings for production load

## 10. Cost Optimization

| Optimization | Savings |
|-------------|---------|
| Redis SERP cache (24h TTL) | 60-70% Serper costs |
| Claude response cache (30min) | 40-50% AI costs |
| Haiku for simple tasks | 30% AI costs |
| Batch Firecrawl nightly | 50% scraping costs |
| Supabase edge functions | Saves webhook workers |

**Estimated monthly cost at 100 customers: ~$330**
