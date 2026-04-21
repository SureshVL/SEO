"""Link-building agent — wraps DataForSEO backlinks data and drafts
outreach emails via Claude.

Responsibilities:
- Pull a domain's backlink profile (summary + anchors + referring domains)
  from DataForSEO.
- Rank prospects by domain authority + relevance.
- Draft personalised outreach emails (intro, broken-link, guest-post) via
  Claude with sensible fallbacks when AI is unavailable.

The agent owns the logic; the route layer deals with persistence and
request/response shapes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.clients.claude_client import HAIKU, SONNET, AIUsageAccumulator, ClaudeClient

logger = logging.getLogger("omnirank.links")


# ── Result dataclasses ────────────────────────────────────────────────────────

VALID_STATUSES = (
    "new", "researching", "contacted", "replied",
    "agreed", "placed", "declined",
)

VALID_TEMPLATES = ("intro", "broken_link", "guest_post", "resource_page")


@dataclass
class BacklinkReport:
    domain: str
    total_backlinks: int = 0
    referring_domains: int = 0
    domain_rank: float = 0.0
    dofollow_ratio: float = 0.0
    top_anchors: list[dict[str, Any]] = field(default_factory=list)
    top_referring: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class OutreachEmail:
    subject: str
    body: str
    template: str
    model_used: str = ""
    cost_usd: float = 0.0
    fallback: bool = False


# ── Agent ─────────────────────────────────────────────────────────────────────

class LinkAgent:
    """Pulls backlink data + drafts outreach emails."""

    def __init__(
        self,
        dataforseo_client: Any = None,
        claude_client: ClaudeClient | None = None,
    ):
        self.dataforseo = dataforseo_client
        self.claude = claude_client
        self.ai_usage = AIUsageAccumulator()

    # ── Backlinks profile ────────────────────────────────────────────────────

    def backlink_profile(
        self,
        domain: str,
        anchors_limit: int = 20,
        referring_limit: int = 20,
    ) -> BacklinkReport:
        """Fetch a domain's backlink profile from DataForSEO."""
        domain = self._normalize_domain(domain)
        report = BacklinkReport(domain=domain)

        if not self.dataforseo:
            report.warnings.append("DataForSEO client not configured — returning empty profile.")
            return report

        try:
            summary = self.dataforseo.backlink_summary(domain)
            report.total_backlinks = getattr(summary, "total_backlinks", 0) or 0
            report.referring_domains = getattr(summary, "referring_domains", 0) or 0
            report.domain_rank = float(getattr(summary, "domain_rank", 0) or 0)
            report.dofollow_ratio = float(getattr(summary, "dofollow_ratio", 0) or 0)
        except Exception as exc:
            logger.warning("backlink_summary failed for %s: %s", domain, exc)
            report.warnings.append(f"Backlink summary unavailable: {exc}")

        try:
            report.top_anchors = self.dataforseo.backlink_anchors(domain, limit=anchors_limit)
        except Exception as exc:
            logger.warning("backlink_anchors failed for %s: %s", domain, exc)
            report.warnings.append(f"Anchors unavailable: {exc}")

        try:
            report.top_referring = self.dataforseo.backlink_referring_domains(
                domain, limit=referring_limit,
            )
        except Exception as exc:
            logger.warning("backlink_referring_domains failed for %s: %s", domain, exc)
            report.warnings.append(f"Referring domains unavailable: {exc}")

        return report

    # ── Outreach email drafting ──────────────────────────────────────────────

    def draft_outreach_email(
        self,
        prospect: dict[str, Any],
        campaign: dict[str, Any] | None = None,
        template: str = "intro",
    ) -> OutreachEmail:
        """Draft a personalised outreach email.

        prospect: {domain, url, contact_name?, contact_email?, notes?, domain_rating?}
        campaign: {sender_name, sender_site, value_prop, target_url?, broken_url?}
        template: intro | broken_link | guest_post | resource_page
        """
        if template not in VALID_TEMPLATES:
            template = "intro"
        campaign = campaign or {}

        if self.claude:
            try:
                return self._draft_via_claude(prospect, campaign, template)
            except Exception as exc:
                logger.warning("Claude outreach draft failed: %s", exc)

        return self._draft_fallback(prospect, campaign, template)

    # ── Prospect scoring ─────────────────────────────────────────────────────

    @staticmethod
    def score_prospect(prospect: dict[str, Any]) -> float:
        """Return a 0-100 opportunity score for a link prospect.

        Heavy weight on domain rating, bonus for dofollow-only referrers, and
        deductions for already-linking sites.
        """
        dr = float(prospect.get("domain_rating") or 0.0)
        referring = int(prospect.get("referring_domains") or 0)
        already_linking = bool(prospect.get("already_linking"))
        contact_email = bool(prospect.get("contact_email"))

        score = 0.0
        score += min(dr, 100.0) * 0.6
        score += min(referring / 1000.0, 1.0) * 15.0
        if contact_email:
            score += 15.0
        if already_linking:
            score -= 40.0
        return round(max(0.0, min(100.0, score)), 1)

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_domain(domain: str) -> str:
        d = (domain or "").strip().lower()
        if d.startswith("http://"):
            d = d[len("http://"):]
        elif d.startswith("https://"):
            d = d[len("https://"):]
        return d.split("/")[0].rstrip("/")

    def _draft_via_claude(
        self,
        prospect: dict[str, Any],
        campaign: dict[str, Any],
        template: str,
    ) -> OutreachEmail:
        system = (
            "You are an expert SEO outreach specialist. Write a short, personalised "
            "email (under 140 words) that feels human and non-spammy. Return JSON "
            'with keys "subject" and "body". Do not invent facts about the prospect.'
        )
        prompt = (
            f"Template type: {template}\n"
            f"Prospect domain: {prospect.get('domain', '')}\n"
            f"Prospect page URL: {prospect.get('url', '')}\n"
            f"Contact name: {prospect.get('contact_name') or 'the team'}\n"
            f"Prospect notes: {prospect.get('notes') or 'none'}\n"
            f"Sender name: {campaign.get('sender_name') or 'Alex'}\n"
            f"Sender site: {campaign.get('sender_site') or ''}\n"
            f"Value proposition: {campaign.get('value_prop') or ''}\n"
            f"Target link URL: {campaign.get('target_url') or ''}\n"
            f"Broken URL (for broken_link template): {campaign.get('broken_url') or ''}\n"
        )
        parsed, resp = self.claude.complete_json(
            messages=[{"role": "user", "content": prompt}],
            system=system,
            model=HAIKU,
            max_tokens=600,
            temperature=0.5,
            use_cache=False,
        )
        self.ai_usage.record(resp)
        subject = str(parsed.get("subject") or "Quick thought").strip()
        body = str(parsed.get("body") or "").strip()
        if not body:
            return self._draft_fallback(prospect, campaign, template)
        return OutreachEmail(
            subject=subject,
            body=body,
            template=template,
            model_used=resp.model,
            cost_usd=resp.cost_usd,
        )

    @staticmethod
    def _draft_fallback(
        prospect: dict[str, Any],
        campaign: dict[str, Any],
        template: str,
    ) -> OutreachEmail:
        name = prospect.get("contact_name") or "there"
        prospect_domain = prospect.get("domain") or "your site"
        sender = campaign.get("sender_name") or "Alex"
        sender_site = campaign.get("sender_site") or ""
        value_prop = campaign.get("value_prop") or "we publish in-depth SEO research"
        target = campaign.get("target_url") or sender_site
        broken = campaign.get("broken_url") or ""

        if template == "broken_link":
            subject = f"Broken link on {prospect_domain}"
            body = (
                f"Hi {name},\n\n"
                f"I was reading through {prospect_domain} and noticed the link to "
                f"{broken or 'an older resource'} 404s. Thought you'd want to know.\n\n"
                f"We recently published {target} covering the same topic — "
                f"happy for you to use it as a replacement if it fits. Either way, "
                f"figured the heads-up was worth it.\n\n"
                f"Best,\n{sender}"
            )
        elif template == "guest_post":
            subject = f"Guest post idea for {prospect_domain}"
            body = (
                f"Hi {name},\n\n"
                f"Long-time reader of {prospect_domain}. I'd love to contribute a "
                f"guest post — {value_prop}. I can send 3 topic pitches aligned with "
                f"your recent editorial calendar.\n\n"
                f"Let me know if that sounds interesting and I'll follow up with outlines.\n\n"
                f"Best,\n{sender}"
            )
        elif template == "resource_page":
            subject = f"Suggestion for your resources page"
            body = (
                f"Hi {name},\n\n"
                f"Came across your resources page on {prospect_domain} — great roundup. "
                f"We recently published {target}, which might be a useful addition: "
                f"{value_prop}.\n\n"
                f"No pressure either way — just wanted to share.\n\n"
                f"Best,\n{sender}"
            )
        else:
            subject = f"Quick note from {sender_site or sender}"
            body = (
                f"Hi {name},\n\n"
                f"I've been following {prospect_domain} and really appreciate your "
                f"work. I run {sender_site or 'a related site'} — {value_prop}.\n\n"
                f"If you're ever looking for collaborators or additional sources for "
                f"your readers, I'd love to stay in touch.\n\n"
                f"Best,\n{sender}"
            )

        return OutreachEmail(
            subject=subject,
            body=body,
            template=template,
            fallback=True,
        )
