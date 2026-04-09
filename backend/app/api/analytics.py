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
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID not configured")
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
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID not configured")
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
    access_token: str
    refresh_token: str | None = None
    email: str | None = None
    properties: list[dict[str, Any]] = []   # GA4 properties or GSC sites
    service: str


@router.post("/exchange-token", response_model=TokenExchangeResponse)
async def exchange_token(req: TokenExchangeRequest):
    """Exchange OAuth code for tokens and fetch available properties/sites."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")

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

        return TokenExchangeResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            email=email,
            properties=properties,
            service=req.service,
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
