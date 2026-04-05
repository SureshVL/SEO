# OMNI-RANK OR-1 — AI SEO Agent Platform

> AI-powered SEO platform built with Claude Sonnet, FastAPI, Next.js 14, and Supabase.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (Next.js 14 + Tailwind + TypeScript)              │
│  Landing · Auth · Dashboard · Research · Keywords · Audit   │
└──────────────────────┬──────────────────────────────────────┘
                       │ REST + SSE
┌──────────────────────▼──────────────────────────────────────┐
│  Backend (FastAPI + Python 3.12)                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Research  │ │ Content  │ │Technical │ │ Keyword  │       │
│  │  Agent   │ │  Agent   │ │  Agent   │ │  Agent   │       │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘       │
│       └──────┬─────┴──────┬─────┴──────┬─────┘             │
│              │   Claude Sonnet API     │                    │
│              │   (with Haiku routing)  │                    │
│              └─────────────────────────┘                    │
│  Serper · Firecrawl · PageSpeed Insights · Redis Cache      │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│  Supabase (PostgreSQL + pgvector + Auth + RLS)              │
│  15 tables · RBAC · Auto-provisioning · Vector embeddings   │
└─────────────────────────────────────────────────────────────┘
```

## What's Built (Weeks 1–4)

### Week 1–2: Foundation
- **Full DB schema**: 15+ tables (orgs, users, projects, keywords, rank_history, billing, etc.)
- **Row Level Security**: Multi-tenant isolation with RBAC (owner/admin/member/viewer)
- **Auth**: Supabase Auth (Google OAuth + email/password) with auto-provisioning
- **Frontend**: 12-page Next.js app with dashboard, research, keywords, audit, content, billing
- **Infra**: Docker, docker-compose (backend + frontend + Redis), GitHub Actions CI

### Week 3–4: AI Core
- **Claude Client**: Anthropic API with retry, caching, model routing (Sonnet/Haiku), cost tracking
- **Research Agent**: SERP collection (Serper) + page scraping (Firecrawl) + Claude-powered scoring
- **Content Agent**: Full article generation with entities, FAQ, meta descriptions, internal links
- **Technical Agent**: Real PageSpeed Insights API + Claude analysis for prioritized fixes
- **Keyword Agent**: AI-powered keyword research with clustering, intent mapping, content planning
- **Workflow**: Clean iterative loop without fake score inflation

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Fill in: ANTHROPIC_API_KEY, SERPER_API_KEY, FIRECRAWL_API_KEY, SUPABASE_*

# 2. Start everything
docker compose up

# 3. Access
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# API docs: http://localhost:8000/docs
```

### Backend only (development)
```bash
cd backend
pip install -e ".[dev]" httpx
uvicorn app.main:app --reload
```

### Frontend only (development)
```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check + AI status |
| POST | `/research/run` | Synchronous AI SEO research |
| POST | `/jobs/research` | Async research job (background) |
| GET | `/jobs` | List all jobs |
| GET | `/jobs/{id}` | Job status + results |
| GET | `/jobs/{id}/stream` | SSE log stream |
| POST | `/keywords/research` | AI keyword strategy |
| POST | `/audit/technical` | PageSpeed + AI audit |
| POST | `/aso/run` | App Store Optimization |
| POST | `/deploy/run` | Deploy bridge |

All endpoints require `X-API-KEY` header.

## Tests

```bash
cd backend && python -m pytest tests/ -v
# 23 tests, all passing
```

## Monthly Cost (100 customers)

| Service | Cost |
|---------|------|
| Supabase Pro | $25 |
| Railway (2 workers) | $20 |
| Vercel Pro | $20 |
| Redis (Upstash) | $10 |
| Claude API (~50K req) | $150 |
| Serper (10K searches) | $50 |
| Firecrawl (5K scrapes) | $40 |
| **Total** | **~$330/mo** |

## Revenue Model

| Plan | Price | Target |
|------|-------|--------|
| Starter | ₹1,999/mo | Small businesses |
| Growth | ₹4,999/mo | Growing companies |
| Agency | ₹14,999/mo | SEO agencies |
| Enterprise | Custom | Large orgs |

Break-even at ~15 customers. 94% gross margin at 100 customers.

## Tech Stack

- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, Recharts, Zustand, Sonner
- **Backend**: FastAPI, Python 3.12, Pydantic v2, httpx
- **AI**: Claude Sonnet 4 (Anthropic API) with Haiku routing
- **Database**: Supabase (PostgreSQL + pgvector + Auth)
- **Cache**: Redis (Upstash serverless)
- **Data**: Serper (SERP), Firecrawl (scraping), PageSpeed Insights (audits)
- **Infra**: Docker, GitHub Actions, Railway/Render
