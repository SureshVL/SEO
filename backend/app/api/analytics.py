"""GA4 and Google Search Console OAuth integration."""

from __future__ import annotations

import logging
import os
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger("omnirank.analytics")
router = APIRouter(prefix="/analytics", tags=["analytics"])


def _db():
    """Lazy import of the Supabase REST helper to avoid a circular import."""
    from app.main import _supabase_rest
    return _supabase_rest


def store_oauth_tokens(
    project_id: str, service: str, access_token: str,
    refresh_token: str | None, expires_in: int | None, email: str | None,
) -> None:
    """Persist Google OAuth tokens server-side, encrypted."""
    if not project_id:
        return
    import time
    from app.core.secrets_crypto import encrypt
    from app.core.pgrest import q, ts
    from datetime import datetime, timezone, timedelta

    db = _db()
    expires_at = None
    if expires_in:
        expires_at = ts(datetime.now(timezone.utc) + timedelta(seconds=int(expires_in) - 60))
    row = {
        "project_id": project_id,
        "service": service,
        "access_token": encrypt(access_token),
        "refresh_token": encrypt(refresh_token) if refresh_token else None,
        "expires_at": expires_at,
        "email": email,
    }
    try:
        existing = db("get", "oauth_tokens",
                      params=f"project_id=eq.{project_id}&service=eq.{q(service)}&select=id")
        existing = existing if isinstance(existing, list) else [existing] if existing else []
        if existing:
            # keep the previous refresh_token if Google didn't return a new one
            if not refresh_token:
                row.pop("refresh_token", None)
            db("patch", f"oauth_tokens?id=eq.{existing[0]['id']}", row)
        else:
            db("post", "oauth_tokens", row)
    except Exception as exc:
        logger.warning("Could not persist oauth tokens: %s", exc)


async def get_valid_access_token(project_id: str, service: str) -> str | None:
    """Return a fresh access token for the project+service, refreshing if needed."""
    import time
    from datetime import datetime, timezone
    from app.core.secrets_crypto import decrypt, encrypt
    from app.core.pgrest import q, ts

    db = _db()
    try:
        rows = db("get", "oauth_tokens",
                  params=f"project_id=eq.{project_id}&service=eq.{q(service)}")
    except Exception:
        return None
    rows = rows if isinstance(rows, list) else [rows] if rows else []
    if not rows:
        return None
    row = rows[0]

    expires_at = row.get("expires_at")
    still_valid = True
    if expires_at:
        try:
            exp = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            still_valid = exp > datetime.now(timezone.utc)
        except ValueError:
            still_valid = True

    if still_valid and row.get("access_token"):
        return decrypt(row["access_token"])

    # refresh
    refresh = decrypt(row["refresh_token"]) if row.get("refresh_token") else ""
    if not refresh or not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return decrypt(row["access_token"]) if row.get("access_token") else None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.post("https://oauth2.googleapis.com/token", data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh,
                "grant_type": "refresh_token",
            })
        if res.status_code == 200:
            t = res.json()
            new_access = t.get("access_token", "")
            store_oauth_tokens(project_id, service, new_access, None,
                               t.get("expires_in"), row.get("email"))
            return new_access
    except Exception as exc:
        logger.warning("Token refresh failed: %s", exc)
    return decrypt(row["access_token"]) if row.get("access_token") else None

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:3000/dashboard/settings")

GA4_SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "openid",
    "email",
]
GSC_SCOPES = [
    "https://www.googleapis.com/auth/webmasters.readonly",
    "openid",
    "email",
]


# ── OAuth flow ────────────────────────────────────────────────────────────────

@router.get("/ga4/auth-url")
def ga4_auth_url(project_id: str = Query(default="")):
    """Return the OAuth URL to redirect the user to Google for GA4 access."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google connection is not set up yet — add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to the backend .env (see Setup steps below).")
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(GA4_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": f"ga4:{project_id}",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return {"auth_url": url}


@router.get("/gsc/auth-url")
def gsc_auth_url(project_id: str = Query(default="")):
    """Return the OAuth URL to redirect the user to Google for GSC access."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google connection is not set up yet — add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to the backend .env (see Setup steps below).")
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(GSC_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": f"gsc:{project_id}",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return {"auth_url": url}


class TokenExchangeRequest(BaseModel):
    code: str
    service: str  # "ga4" | "gsc"
    project_id: str = ""


class TokenExchangeResponse(BaseModel):
    # access/refresh tokens are intentionally NOT returned to the browser; they
    # are stored server-side (encrypted) and used by the backend. `connected`
    # signals success. Fields kept optional for backward compatibility.
    access_token: str = ""
    refresh_token: str | None = None
    email: str | None = None
    properties: list[dict[str, Any]] = []   # GA4 properties or GSC sites
    service: str
    connected: bool = False


@router.post("/exchange-token", response_model=TokenExchangeResponse)
async def exchange_token(req: TokenExchangeRequest):
    """Exchange OAuth code for tokens and fetch available properties/sites."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Google connection is not set up yet — add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to the backend .env (see Setup steps below).")

    async with httpx.AsyncClient() as client:
        # Exchange code for tokens
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": req.code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        if token_res.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Token exchange failed: {token_res.text}")

        tokens = token_res.json()
        access_token = tokens.get("access_token", "")
        refresh_token = tokens.get("refresh_token")

        # Get user email
        user_res = await client.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        email = user_res.json().get("email") if user_res.status_code == 200 else None

        properties: list[dict[str, Any]] = []

        if req.service == "ga4":
            # Fetch GA4 account summaries
            props_res = await client.get(
                "https://analyticsadmin.googleapis.com/v1beta/accountSummaries",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if props_res.status_code == 200:
                summaries = props_res.json().get("accountSummaries", [])
                for account in summaries:
                    for prop in account.get("propertySummaries", []):
                        properties.append({
                            "property_id": prop.get("property", "").replace("properties/", ""),
                            "display_name": prop.get("displayName", ""),
                            "account": account.get("displayName", ""),
                        })

        elif req.service == "gsc":
            # Fetch GSC verified sites
            sites_res = await client.get(
                "https://www.googleapis.com/webmasters/v3/sites",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if sites_res.status_code == 200:
                for site in sites_res.json().get("siteEntry", []):
                    properties.append({
                        "site_url": site.get("siteUrl", ""),
                        "permission_level": site.get("permissionLevel", ""),
                    })

        # Persist tokens server-side (encrypted). Do NOT return them to the
        # browser - that was the localStorage exposure we are closing.
        if req.project_id:
            store_oauth_tokens(
                req.project_id, req.service, access_token, refresh_token,
                tokens.get("expires_in"), email,
            )

        return TokenExchangeResponse(
            email=email,
            properties=properties,
            service=req.service,
            connected=True,
        )


# ── Revenue attribution data ──────────────────────────────────────────────────

class GA4MetricsRequest(BaseModel):
    access_token: str
    property_id: str
    date_range: str = "30daysAgo"  # e.g. "30daysAgo", "90daysAgo"


@router.post("/ga4/metrics")
async def fetch_ga4_metrics(req: GA4MetricsRequest):
    """Fetch sessions, revenue, and organic traffic from GA4."""
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"https://analyticsdata.googleapis.com/v1beta/properties/{req.property_id}:runReport",
            headers={"Authorization": f"Bearer {req.access_token}", "Content-Type": "application/json"},
            json={
                "dateRanges": [{"startDate": req.date_range, "endDate": "today"}],
                "dimensions": [{"name": "sessionDefaultChannelGroup"}],
                "metrics": [
                    {"name": "sessions"},
                    {"name": "totalRevenue"},
                    {"name": "conversions"},
                    {"name": "newUsers"},
                ],
            },
        )
        if res.status_code != 200:
            raise HTTPException(status_code=400, detail=f"GA4 API error: {res.text}")

        data = res.json()
        rows = data.get("rows", [])
        organic = {}
        total = {"sessions": 0, "revenue": 0.0, "conversions": 0, "new_users": 0}

        for row in rows:
            channel = row["dimensionValues"][0]["value"]
            sessions = int(row["metricValues"][0]["value"])
            revenue = float(row["metricValues"][1]["value"])
            conversions = int(row["metricValues"][2]["value"])
            new_users = int(row["metricValues"][3]["value"])
            total["sessions"] += sessions
            total["revenue"] += revenue
            total["conversions"] += conversions
            total["new_users"] += new_users
            if "organic" in channel.lower():
                organic = {
                    "sessions": sessions,
                    "revenue": revenue,
                    "conversions": conversions,
                    "new_users": new_users,
                }

        organic_share = (organic.get("sessions", 0) / total["sessions"] * 100) if total["sessions"] else 0
        return {
            "total": total,
            "organic": organic,
            "organic_share_pct": round(organic_share, 1),
            "date_range": req.date_range,
            "property_id": req.property_id,
        }


class GSCMetricsRequest(BaseModel):
    access_token: str
    site_url: str
    date_range_days: int = 30


@router.post("/gsc/metrics")
async def fetch_gsc_metrics(req: GSCMetricsRequest):
    """Fetch click/impression data from Google Search Console."""
    from datetime import date, timedelta
    end = date.today().isoformat()
    start = (date.today() - timedelta(days=req.date_range_days)).isoformat()

    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"https://www.googleapis.com/webmasters/v3/sites/{req.site_url}/searchAnalytics/query",
            headers={"Authorization": f"Bearer {req.access_token}", "Content-Type": "application/json"},
            json={
                "startDate": start,
                "endDate": end,
                "dimensions": ["query"],
                "rowLimit": 25,
                "startRow": 0,
            },
        )
        if res.status_code != 200:
            raise HTTPException(status_code=400, detail=f"GSC API error: {res.text}")

        data = res.json()
        rows = data.get("rows", [])
        top_queries = [
            {
                "query": r["keys"][0],
                "clicks": r.get("clicks", 0),
                "impressions": r.get("impressions", 0),
                "ctr": round(r.get("ctr", 0) * 100, 1),
                "position": round(r.get("position", 0), 1),
            }
            for r in rows
        ]
        totals = {
            "clicks": sum(r.get("clicks", 0) for r in rows),
            "impressions": sum(r.get("impressions", 0) for r in rows),
            "avg_ctr": round(sum(r.get("ctr", 0) for r in rows) / len(rows) * 100, 1) if rows else 0,
            "avg_position": round(sum(r.get("position", 0) for r in rows) / len(rows), 1) if rows else 0,
        }
        return {
            "site_url": req.site_url,
            "date_range_days": req.date_range_days,
            "totals": totals,
            "top_queries": top_queries,
        }


# ── Combined attribution report ───────────────────────────────────────────────

class AttributionRequest(BaseModel):
    # tokens are optional: when project_id is given, the backend uses the
    # server-side stored tokens instead of trusting tokens from the browser.
    ga4_access_token: str = ""
    ga4_property_id: str
    gsc_access_token: str = ""
    gsc_site_url: str
    date_range_days: int = 30
    top_n: int = 15
    project_id: str = ""


async def _ga4_pages(
    client: httpx.AsyncClient,
    access_token: str,
    property_id: str,
    start: str,
    end: str,
) -> list[dict[str, Any]]:
    """Return landing-page × channel metrics from GA4."""
    res = await client.post(
        f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={
            "dateRanges": [{"startDate": start, "endDate": end}],
            "dimensions": [
                {"name": "landingPagePlusQueryString"},
                {"name": "sessionDefaultChannelGroup"},
            ],
            "metrics": [
                {"name": "sessions"},
                {"name": "totalRevenue"},
                {"name": "conversions"},
            ],
            "limit": 200,
        },
    )
    if res.status_code != 200:
        raise HTTPException(status_code=400, detail=f"GA4 landing-page API error: {res.text}")
    rows = res.json().get("rows", [])
    return [
        {
            "page_path": r["dimensionValues"][0]["value"],
            "channel": r["dimensionValues"][1]["value"],
            "sessions": int(r["metricValues"][0]["value"]),
            "revenue": float(r["metricValues"][1]["value"]),
            "conversions": int(r["metricValues"][2]["value"]),
        }
        for r in rows
    ]


async def _ga4_channel_totals(
    client: httpx.AsyncClient,
    access_token: str,
    property_id: str,
    start: str,
    end: str,
) -> list[dict[str, Any]]:
    res = await client.post(
        f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={
            "dateRanges": [{"startDate": start, "endDate": end}],
            "dimensions": [{"name": "sessionDefaultChannelGroup"}],
            "metrics": [
                {"name": "sessions"},
                {"name": "totalRevenue"},
                {"name": "conversions"},
                {"name": "newUsers"},
            ],
        },
    )
    if res.status_code != 200:
        raise HTTPException(status_code=400, detail=f"GA4 channels API error: {res.text}")
    rows = res.json().get("rows", [])
    return [
        {
            "channel": r["dimensionValues"][0]["value"],
            "sessions": int(r["metricValues"][0]["value"]),
            "revenue": float(r["metricValues"][1]["value"]),
            "conversions": int(r["metricValues"][2]["value"]),
            "new_users": int(r["metricValues"][3]["value"]),
        }
        for r in rows
    ]


async def _gsc_query(
    client: httpx.AsyncClient,
    access_token: str,
    site_url: str,
    start: str,
    end: str,
    dimensions: list[str],
    row_limit: int = 200,
) -> list[dict[str, Any]]:
    res = await client.post(
        f"https://www.googleapis.com/webmasters/v3/sites/{site_url}/searchAnalytics/query",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={
            "startDate": start, "endDate": end,
            "dimensions": dimensions,
            "rowLimit": row_limit,
            "startRow": 0,
        },
    )
    if res.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=f"GSC API error ({','.join(dimensions)}): {res.text}",
        )
    rows = res.json().get("rows", [])
    out: list[dict[str, Any]] = []
    for r in rows:
        keys = r.get("keys", [])
        row: dict[str, Any] = {
            "clicks": int(r.get("clicks", 0)),
            "impressions": int(r.get("impressions", 0)),
            "ctr": float(r.get("ctr", 0.0)),
            "position": float(r.get("position", 0.0)),
        }
        for dim, val in zip(dimensions, keys):
            row[dim] = val
        out.append(row)
    return out


@router.post("/attribution")
async def attribution_report(req: AttributionRequest):
    """Pull GA4 + GSC data and merge into a revenue-attribution report."""
    from datetime import date, timedelta
    from app.agents.attribution_agent import AttributionAgent

    end = date.today().isoformat()
    start = (date.today() - timedelta(days=req.date_range_days)).isoformat()

    # Prefer server-side stored tokens; fall back to any tokens in the request
    # (legacy clients) so this stays backward compatible during rollout.
    ga4_token = req.ga4_access_token
    gsc_token = req.gsc_access_token
    if req.project_id:
        ga4_token = (await get_valid_access_token(req.project_id, "ga4")) or ga4_token
        gsc_token = (await get_valid_access_token(req.project_id, "gsc")) or gsc_token
    if not ga4_token or not gsc_token:
        raise HTTPException(status_code=400, detail="GA4/GSC not connected for this project")

    async with httpx.AsyncClient(timeout=30.0) as client:
        ga4_pages = await _ga4_pages(client, ga4_token, req.ga4_property_id, start, end)
        ga4_channels = await _ga4_channel_totals(client, ga4_token, req.ga4_property_id, start, end)
        gsc_queries = await _gsc_query(
            client, gsc_token, req.gsc_site_url, start, end,
            dimensions=["query"], row_limit=200,
        )
        gsc_pages = await _gsc_query(
            client, gsc_token, req.gsc_site_url, start, end,
            dimensions=["page"], row_limit=200,
        )
        gsc_page_queries = await _gsc_query(
            client, gsc_token, req.gsc_site_url, start, end,
            dimensions=["page", "query"], row_limit=500,
        )

    # Normalise GSC rows (dimensions end up as key names like "query" / "page")
    gsc_queries_norm = [_gsc_row_normalised(r, ["query"]) for r in gsc_queries]
    gsc_pages_norm = [_gsc_row_normalised(r, ["page"]) for r in gsc_pages]
    gsc_page_queries_norm = [_gsc_row_normalised(r, ["page", "query"]) for r in gsc_page_queries]

    report = AttributionAgent().build_report(
        date_range_days=req.date_range_days,
        ga4_property_id=req.ga4_property_id,
        gsc_site_url=req.gsc_site_url,
        ga4_pages=ga4_pages,
        ga4_channel_totals=ga4_channels,
        gsc_queries=gsc_queries_norm,
        gsc_pages=gsc_pages_norm,
        gsc_page_queries=gsc_page_queries_norm,
        top_n=req.top_n,
    )
    return _serialise_attribution(report)


def _gsc_row_normalised(row: dict[str, Any], dims: list[str]) -> dict[str, Any]:
    """GSC helper rows include raw dimension values under their dim name —
    pass through unchanged (the agent reads `page` / `query` keys directly)."""
    return row


def _serialise_attribution(report) -> dict[str, Any]:
    return {
        "date_range_days": report.date_range_days,
        "ga4_property_id": report.ga4_property_id,
        "gsc_site_url": report.gsc_site_url,
        "ga4": {
            "total_sessions": report.total_sessions,
            "organic_sessions": report.organic_sessions,
            "organic_share_pct": report.organic_share_pct,
            "total_revenue": report.total_revenue,
            "organic_revenue": report.organic_revenue,
            "organic_revenue_share_pct": report.organic_revenue_share_pct,
            "total_conversions": report.total_conversions,
            "organic_conversions": report.organic_conversions,
        },
        "gsc": {
            "total_clicks": report.gsc_total_clicks,
            "total_impressions": report.gsc_total_impressions,
            "avg_position": report.gsc_avg_position,
        },
        "top_pages": [
            {
                "page_path": p.page_path,
                "sessions": p.sessions,
                "organic_sessions": p.organic_sessions,
                "revenue": round(p.revenue, 2),
                "organic_revenue": round(p.organic_revenue, 2),
                "conversions": p.conversions,
                "gsc_clicks": p.gsc_clicks,
                "gsc_impressions": p.gsc_impressions,
                "avg_position": p.avg_position,
                "top_queries": p.top_queries,
            }
            for p in report.top_pages
        ],
        "top_queries": [
            {
                "query": q.query,
                "clicks": q.clicks,
                "impressions": q.impressions,
                "ctr": q.ctr,
                "position": q.position,
                "landing_pages": q.landing_pages,
                "attributed_revenue": q.attributed_revenue,
            }
            for q in report.top_queries
        ],
        "warnings": report.warnings,
    }
