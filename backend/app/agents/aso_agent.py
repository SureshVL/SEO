from __future__ import annotations

import re

from app.schemas.aso import (
    AsoRequest,
    AsoResponse,
    LocaleMetadata,
    ReviewResponseTemplate,
)


LOCALE_HINTS: dict[str, dict[str, str]] = {
    "en-US": {
        "value_prop": "AI SEO insights",
        "cta": "Grow organic traffic faster",
    },
    "es-ES": {
        "value_prop": "información SEO con IA",
        "cta": "Impulsa el tráfico orgánico",
    },
    "pt-BR": {
        "value_prop": "insights de SEO com IA",
        "cta": "Aumente o tráfego orgânico",
    },
    "fr-FR": {
        "value_prop": "insights SEO IA",
        "cta": "Accélérez votre trafic organique",
    },
}


class AsoAgent:
    """Generate localized app-store metadata and review playbooks."""

    def _extract_review_themes(self, reviews: list[str]) -> list[str]:
        buckets = {
            "performance": ["slow", "lag", "crash", "freeze"],
            "ux": ["easy", "hard", "confusing", "simple"],
            "pricing": ["price", "expensive", "value", "subscription"],
            "support": ["support", "response", "help", "ticket"],
        }
        text = " ".join(r.lower() for r in reviews)
        themes = []
        for theme, terms in buckets.items():
            if any(t in text for t in terms):
                themes.append(theme)
        return themes

    def run(self, request: AsoRequest) -> AsoResponse:
        platform = self._detect_platform(str(request.app_link))
        metadata = [self._build_locale_metadata(request, locale) for locale in request.locales]

        notes = [
            "Run weekly title/subtitle experiments and keep one variable per test.",
            "Map top competitor review complaints to roadmap + store listing copy updates.",
            "Refresh first 170 chars of description monthly to reflect latest ranking terms.",
        ]
        if platform == "google-play":
            notes.append("Use short description as keyword-dense hook; prioritize conversion intent.")
        else:
            notes.append("Keep App Store keyword field comma-separated and avoid duplicated title terms.")

        return AsoResponse(
            platform=platform,
            metadata=metadata,
            review_response_playbook=self._review_playbook(request.app_name),
            optimization_notes=notes,
            review_themes=self._extract_review_themes(request.recent_reviews),
        )

    def _build_locale_metadata(self, request: AsoRequest, locale: str) -> LocaleMetadata:
        hints = LOCALE_HINTS.get(locale, LOCALE_HINTS["en-US"])
        app_name = request.app_name.strip()
        primary = request.primary_keyword.strip()

        base_terms = [primary] + [k.strip() for k in request.secondary_keywords if k.strip()]
        keyword_field = self._keyword_field(base_terms)

        title_variants = [
            self._clip(f"{app_name}: {primary}", 30),
            self._clip(f"{app_name} — {hints['value_prop']}", 30),
            self._clip(f"{primary} & Growth | {app_name}", 30),
        ]

        subtitle = self._clip(f"{hints['value_prop']} · {hints['cta']}", 30)

        short_description = self._clip(
            f"{app_name} delivers {hints['value_prop']} with automated competitor tracking, keyword opportunities, and content actions.",
            80,
        )

        return LocaleMetadata(
            locale=locale,
            title_variants=self._unique(title_variants),
            subtitle=subtitle,
            keyword_field=keyword_field,
            short_description=short_description,
        )

    @staticmethod
    def _review_playbook(app_name: str) -> list[ReviewResponseTemplate]:
        return [
            ReviewResponseTemplate(
                sentiment="positive",
                response_template=(
                    f"Thanks for the great feedback on {app_name}! "
                    "If you share which feature helped most, we can prioritize similar improvements."
                ),
            ),
            ReviewResponseTemplate(
                sentiment="neutral",
                response_template=(
                    "Thanks for trying the app. We'd love one thing that would make this a 5-star experience for you."
                ),
            ),
            ReviewResponseTemplate(
                sentiment="negative",
                response_template=(
                    "We’re sorry for the friction. Please send device/version details and issue steps so our team can fix this quickly."
                ),
            ),
        ]

    @staticmethod
    def _detect_platform(app_link: str) -> str:
        link = app_link.lower()
        if "play.google.com" in link:
            return "google-play"
        if "apps.apple.com" in link:
            return "app-store"
        return "unknown"

    @staticmethod
    def _keyword_field(terms: list[str]) -> str:
        deduped: list[str] = []
        seen: set[str] = set()
        for term in terms:
            normalized = re.sub(r"\s+", " ", term.lower()).strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                deduped.append(normalized)
        return ",".join(deduped)[:95]

    @staticmethod
    def _clip(text: str, max_len: int) -> str:
        return text[:max_len].rstrip()

    @staticmethod
    def _unique(items: list[str]) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()
        for item in items:
            if item not in seen:
                seen.add(item)
                ordered.append(item)
        return ordered
