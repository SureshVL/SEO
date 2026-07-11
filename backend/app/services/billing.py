"""Razorpay billing integration.

Handles subscription creation, plan changes, webhook processing,
and usage limit enforcement.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("omnirank.billing")

PLANS = {
    "starter": {
        "name": "Starter",
        "price_inr": 1999,          # rupees (display + test)
        "price_paise": 199900,      # paise (Razorpay API)
        "price_usd": 29,            # international pricing (Stripe)
        "currency": "INR",
        "max_projects": 1,
        "max_keywords": 50,
        "max_reports_per_month": 5,
        "razorpay_plan_id": "",     # set via env
    },
    "growth": {
        "name": "Growth",
        "price_inr": 4999,
        "price_paise": 499900,
        "price_usd": 79,
        "currency": "INR",
        "max_projects": 5,
        "max_keywords": 300,
        "max_reports_per_month": 999,
        "razorpay_plan_id": "",
    },
    "agency": {
        "name": "Agency",
        "price_inr": 14999,
        "price_paise": 1499900,
        "price_usd": 199,
        "currency": "INR",
        "max_projects": 25,
        "max_keywords": 2000,
        "max_reports_per_month": 999,
        "razorpay_plan_id": "",
    },
}


@dataclass
class SubscriptionResult:
    subscription_id: str
    short_url: str  # Razorpay checkout link
    status: str


class RazorpayClient:
    """Razorpay API client for subscription management."""

    def __init__(
        self,
        key_id: str | None = None,
        key_secret: str | None = None,
    ):
        self.key_id = key_id or settings.razorpay_key_id
        self.key_secret = key_secret or settings.razorpay_key_secret
        self.base_url = "https://api.razorpay.com/v1"

        if not self.key_id or not self.key_secret:
            logger.warning("Razorpay credentials not set — billing disabled")

    @property
    def enabled(self) -> bool:
        return bool(self.key_id and self.key_secret)

    def create_subscription(
        self,
        plan_id: str,
        customer_email: str,
        customer_name: str = "",
        total_count: int = 12,  # 12 months
        org_id: str = "",
        plan_name: str = "",
    ) -> SubscriptionResult:
        """Create a new subscription and return checkout link."""
        if not self.enabled:
            raise ValueError("Razorpay not configured")

        payload = {
            "plan_id": plan_id,
            "total_count": total_count,
            "quantity": 1,
            "customer_notify": 1,
            "notes": {
                "email": customer_email,
                "name": customer_name,
                # webhooks activate the org via these - they are required
                "org_id": org_id,
                "plan": plan_name,
            },
        }

        with httpx.Client(auth=(self.key_id, self.key_secret), timeout=30) as client:
            resp = client.post(f"{self.base_url}/subscriptions", json=payload)
            resp.raise_for_status()
            data = resp.json()

        return SubscriptionResult(
            subscription_id=data["id"],
            short_url=data.get("short_url", ""),
            status=data.get("status", "created"),
        )

    def cancel_subscription(self, subscription_id: str, cancel_at_cycle_end: bool = True) -> dict:
        """Cancel a subscription."""
        if not self.enabled:
            raise ValueError("Razorpay not configured")

        with httpx.Client(auth=(self.key_id, self.key_secret), timeout=30) as client:
            resp = client.post(
                f"{self.base_url}/subscriptions/{subscription_id}/cancel",
                json={"cancel_at_cycle_end": cancel_at_cycle_end},
            )
            resp.raise_for_status()
            return resp.json()

    def get_subscription(self, subscription_id: str) -> dict:
        """Get subscription details."""
        if not self.enabled:
            return {}

        with httpx.Client(auth=(self.key_id, self.key_secret), timeout=30) as client:
            resp = client.get(f"{self.base_url}/subscriptions/{subscription_id}")
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    def verify_webhook_signature(body: bytes, signature: str, secret: str | None = None) -> bool:
        """Verify Razorpay webhook signature."""
        webhook_secret = secret or settings.razorpay_webhook_secret
        if not webhook_secret:
            return False
        expected = hmac.new(webhook_secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


# Deep-crawl page budgets. Free trials get a hard cap; paid plans unlock
# template-aware crawling of large sites.
CRAWL_BUDGETS = {
    "trial": 25,
    "starter": 100,
    "growth": 1000,
    "agency": 5000,
    "enterprise": 10000,
}


def crawl_budget_for(plan: str | None, plan_status: str | None) -> int:
    """Max pages per crawl for an org. Anything not actively paying = trial cap."""
    if plan_status != "active":
        return CRAWL_BUDGETS["trial"]
    return CRAWL_BUDGETS.get(plan or "", CRAWL_BUDGETS["trial"])


def stripe_price_id_for(plan: str) -> str:
    """Stripe recurring Price ID for a plan, configured via env."""
    return {
        "starter": settings.stripe_price_starter,
        "growth": settings.stripe_price_growth,
        "agency": settings.stripe_price_agency,
    }.get(plan, "")


class StripeClient:
    """Stripe API client (REST, no SDK) for international subscriptions."""

    def __init__(self, secret_key: str | None = None):
        self.secret_key = secret_key or settings.stripe_secret_key
        self.base_url = "https://api.stripe.com/v1"
        if not self.secret_key:
            logger.warning("Stripe credentials not set — international billing disabled")

    @property
    def enabled(self) -> bool:
        return bool(self.secret_key)

    def create_checkout_session(
        self,
        plan: str,
        org_id: str,
        customer_email: str = "",
    ) -> dict:
        """Create a Stripe Checkout session for a subscription plan."""
        if not self.enabled:
            raise RuntimeError("Stripe not configured")

        price_id = stripe_price_id_for(plan)
        if not price_id:
            raise ValueError(f"Stripe price ID not configured for plan '{plan}'")

        base = settings.app_base_url.rstrip("/")
        form: dict[str, str] = {
            "mode": "subscription",
            "line_items[0][price]": price_id,
            "line_items[0][quantity]": "1",
            "success_url": f"{base}/dashboard/billing?status=success",
            "cancel_url": f"{base}/dashboard/billing?status=cancelled",
            "metadata[org_id]": org_id,
            "metadata[plan]": plan,
            "subscription_data[metadata][org_id]": org_id,
            "subscription_data[metadata][plan]": plan,
            "allow_promotion_codes": "true",
        }
        if customer_email:
            form["customer_email"] = customer_email

        with httpx.Client(auth=(self.secret_key, ""), timeout=30) as client:
            resp = client.post(f"{self.base_url}/checkout/sessions", data=form)
            resp.raise_for_status()
            data = resp.json()
        return {"checkout_url": data.get("url"), "session_id": data.get("id")}

    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> dict:
        if not self.enabled:
            return {}
        with httpx.Client(auth=(self.secret_key, ""), timeout=30) as client:
            if at_period_end:
                resp = client.post(
                    f"{self.base_url}/subscriptions/{subscription_id}",
                    data={"cancel_at_period_end": "true"},
                )
            else:
                resp = client.delete(f"{self.base_url}/subscriptions/{subscription_id}")
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    def verify_webhook_signature(
        body: bytes,
        sig_header: str,
        secret: str | None = None,
        tolerance_seconds: int = 300,
    ) -> bool:
        """Verify a Stripe webhook signature (t=...,v1=... scheme)."""
        import time as _time

        webhook_secret = secret or settings.stripe_webhook_secret
        if not webhook_secret or not sig_header:
            return False

        parts = dict(
            item.split("=", 1) for item in sig_header.split(",") if "=" in item
        )
        timestamp = parts.get("t", "")
        candidates = [v for k, v in parts.items() if k == "v1"]
        # multiple v1 signatures can be present; dict keeps only the last,
        # so also scan manually
        candidates = [
            item.split("=", 1)[1]
            for item in sig_header.split(",")
            if item.startswith("v1=")
        ] or candidates
        if not timestamp or not candidates:
            return False

        try:
            if abs(_time.time() - int(timestamp)) > tolerance_seconds:
                return False
        except ValueError:
            return False

        signed_payload = f"{timestamp}.".encode() + body
        expected = hmac.new(webhook_secret.encode(), signed_payload, hashlib.sha256).hexdigest()
        return any(hmac.compare_digest(expected, c) for c in candidates)


class UsageLimiter:
    """Check and enforce plan usage limits."""

    def __init__(self, supabase_url: str, supabase_key: str):
        self.base = supabase_url.rstrip("/") + "/rest/v1"
        self.headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
        }

    def check_project_limit(self, org_id: str) -> tuple[bool, str]:
        """Check if org can create more projects."""
        import requests

        # Get org plan
        org_resp = requests.get(
            f"{self.base}/organizations?id=eq.{org_id}&select=plan,max_projects",
            headers=self.headers, timeout=10,
        )
        if org_resp.status_code != 200:
            return False, "Failed to check limits"
        orgs = org_resp.json()
        if not orgs:
            return False, "Organization not found"

        max_projects = orgs[0].get("max_projects", 1)

        # Count current projects
        proj_resp = requests.get(
            f"{self.base}/projects?org_id=eq.{org_id}&status=eq.active&select=id",
            headers={**self.headers, "Prefer": "count=exact"},
            timeout=10,
        )
        count = len(proj_resp.json()) if proj_resp.status_code == 200 else 0

        if count >= max_projects:
            return False, f"Project limit reached ({count}/{max_projects}). Upgrade your plan."
        return True, ""

    def check_keyword_limit(self, org_id: str) -> tuple[bool, str]:
        """Check if org can add more keywords."""
        import requests

        org_resp = requests.get(
            f"{self.base}/organizations?id=eq.{org_id}&select=plan,max_keywords",
            headers=self.headers, timeout=10,
        )
        if org_resp.status_code != 200:
            return False, "Failed to check limits"
        orgs = org_resp.json()
        if not orgs:
            return False, "Organization not found"

        max_kw = orgs[0].get("max_keywords", 50)

        # Count keywords across all org projects
        kw_resp = requests.get(
            f"{self.base}/keywords?select=id,project_id!inner(org_id)&project_id.org_id=eq.{org_id}",
            headers={**self.headers, "Prefer": "count=exact"},
            timeout=10,
        )
        count = len(kw_resp.json()) if kw_resp.status_code == 200 else 0

        if count >= max_kw:
            return False, f"Keyword limit reached ({count}/{max_kw}). Upgrade your plan."
        return True, ""

    def record_usage(self, org_id: str, metric_type: str, count: int = 1) -> None:
        """Record a usage event for metering."""
        import requests
        requests.post(
            f"{self.base}/usage_metrics",
            headers={**self.headers, "Prefer": "return=minimal"},
            json={"org_id": org_id, "metric_type": metric_type, "count": count},
            timeout=10,
        )
