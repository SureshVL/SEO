"""Email notification service via Resend API.

Handles transactional emails: welcome, reports ready, rank alerts, billing.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("omnirank.email")

TEMPLATES = {
    "welcome": {
        "subject": "Welcome to OMNI-RANK — Let's get you ranking #1",
        "body": """Hi {name},

Welcome to OMNI-RANK! Your AI-powered SEO command center is ready.

Here's how to get started in 3 steps:
1. Create your first project at {app_url}/dashboard/projects
2. Run an AI Research analysis on your website
3. Review your SEO score and start implementing recommendations

Your account comes with 10 free credits and a 14-day trial of all features.

Questions? Reply to this email — we read everything.

— The OMNI-RANK Team""",
    },
    "report_ready": {
        "subject": "Your SEO Report is Ready — {project_name}",
        "body": """Hi {name},

Your {report_type} report for {project_name} is ready to view.

Key highlights:
{summary}

View the full report: {report_url}

— OMNI-RANK""",
    },
    "rank_alert": {
        "subject": "Rank Change Alert: {keyword} {direction} {change} positions",
        "body": """Hi {name},

Your keyword "{keyword}" has {direction} {change} positions.

Previous position: #{previous}
Current position: #{current}

This change was detected for {domain} in {region}.

View details: {app_url}/dashboard/rank-tracker

— OMNI-RANK""",
    },
    "billing_success": {
        "subject": "Payment Received — OMNI-RANK {plan} Plan",
        "body": """Hi {name},

Your payment of {amount} for the {plan} plan has been received.

Your subscription is active until {period_end}.

Manage billing: {app_url}/dashboard/billing

— OMNI-RANK""",
    },
    "trial_ending": {
        "subject": "Your OMNI-RANK trial ends in {days} days",
        "body": """Hi {name},

Your 14-day free trial ends in {days} days.

During your trial, you've:
- Analyzed {research_count} pages with AI
- Tracked {keyword_count} keywords
- Generated {report_count} reports

To keep access to all features, choose a plan: {app_url}/dashboard/billing

Plans start at just ₹1,999/month.

— OMNI-RANK""",
    },
}


class EmailService:
    """Send transactional emails via Resend."""

    def __init__(self, api_key: str | None = None, from_email: str = "OMNI-RANK <noreply@omnirank.app>"):
        self.api_key = api_key or settings.resend_api_key
        self.from_email = from_email
        self.app_url = "https://app.omnirank.app"  # configure per env

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def send(self, to: str, template: str, variables: dict[str, Any] | None = None) -> bool:
        """Send a templated email."""
        if not self.enabled:
            logger.warning("Email not sent (Resend not configured): %s -> %s", template, to)
            return False

        tmpl = TEMPLATES.get(template)
        if not tmpl:
            logger.error("Unknown email template: %s", template)
            return False

        vars = {**(variables or {}), "app_url": self.app_url}
        subject = tmpl["subject"].format_map(SafeDict(vars))
        body = tmpl["body"].format_map(SafeDict(vars))

        try:
            with httpx.Client(timeout=15) as client:
                resp = client.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "from": self.from_email,
                        "to": [to],
                        "subject": subject,
                        "text": body,
                    },
                )
                resp.raise_for_status()
                logger.info("Email sent: %s -> %s", template, to)
                return True
        except Exception as exc:
            logger.error("Email send failed: %s -> %s: %s", template, to, exc)
            return False

    def send_welcome(self, to: str, name: str) -> bool:
        return self.send(to, "welcome", {"name": name})

    def send_rank_alert(
        self, to: str, name: str, keyword: str,
        previous: int, current: int, domain: str, region: str,
    ) -> bool:
        change = abs(previous - current)
        direction = "improved" if current < previous else "dropped"
        return self.send(to, "rank_alert", {
            "name": name, "keyword": keyword, "direction": direction,
            "change": str(change), "previous": str(previous),
            "current": str(current), "domain": domain, "region": region,
        })

    def send_report_ready(self, to: str, name: str, project_name: str, report_type: str, summary: str, report_url: str) -> bool:
        return self.send(to, "report_ready", {
            "name": name, "project_name": project_name,
            "report_type": report_type, "summary": summary, "report_url": report_url,
        })


class SafeDict(dict):
    """Dict that returns {key} for missing keys instead of raising KeyError."""
    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"
