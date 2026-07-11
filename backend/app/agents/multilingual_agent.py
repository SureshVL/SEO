"""Multilingual SEO - translate content, manage hreflang, localize for regions."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from app.clients.llm import llm_client

logger = logging.getLogger("omnirank.multilingual")


@dataclass
class LocalizedContent:
    """Translated and localized content for a language."""
    source_url: str
    localized_url: str
    title: str
    description: str
    content: str
    keywords: list[str]
    needs_review: bool = False


@dataclass
class HreflangLink:
    """Hreflang relationship between language versions."""
    source_url: str
    target_url: str
    target_language: str
    relationship_type: str


@dataclass
class RegionalVariant:
    """Regional content adaptation."""
    region_code: str
    region_name: str
    target_keywords: list[str]
    local_content_needed: bool
    priority: int


class MultilingualAgent:
    """Manages multilingual SEO strategies and content localization."""

    def __init__(self):
        self.llm = llm_client

    async def localize_content(
        self,
        source_url: str,
        source_content: str,
        source_title: str,
        source_keywords: list[str],
        target_language: str,
        target_region: str | None = None,
    ) -> LocalizedContent:
        """Translate and localize content for a target language/region."""
        try:
            region_info = f" (for {target_region})" if target_region else ""
            region_hint = f"\n- {target_region}-specific context and keywords" if target_region else ""

            prompt = f"""Translate and localize this SEO content to {target_language}{region_info}.

Source Title: {source_title}
Source Keywords: {', '.join(source_keywords)}

Source Content:
{source_content[:2000]}

Provide:
1. Localized title (SEO-optimized for {target_language})
2. Localized meta description (160 chars)
3. Localized content (maintain structure, adapt for region)
4. Localized keywords for {target_language}
5. Flag if professional review needed (cultural sensitivity, local terms)

Consider:
- Cultural adaptation (idioms, references, units)
- Search behavior differences in {target_language} markets
- Regional terminology and preferences{region_hint}

Format as JSON:
{{
  "title": "Translated title",
  "description": "Translated meta description",
  "content": "Full translated content with markdown formatting",
  "keywords": ["keyword1", "keyword2"],
  "needs_review": false,
  "adaptation_notes": "What was changed for localization"
}}"""

            response = await self.llm.agenerate_text(
                prompt,
                model="claude-opus-4-8",
                max_tokens=2500,
            )

            localized = self._parse_localized_content(response, source_url)
            return localized

        except Exception as exc:
            logger.error("Content localization failed: %s", exc)
            raise

    async def generate_hreflang_strategy(
        self,
        source_url: str,
        available_languages: list[dict[str, str]],
        is_regional_variant: bool = False,
    ) -> list[HreflangLink]:
        """Generate hreflang tag strategy for language versions."""
        try:
            languages_list = "\n".join(
                f"- {lang['code']}: {lang['name']}"
                for lang in available_languages[:20]
            )

            prompt = f"""Design hreflang strategy for: {source_url}

Available language versions:
{languages_list}

Determine:
1. Which language versions should be linked (all or subset?)
2. URL patterns for each language version
3. Self-referential hreflang for source language
4. x-default version (if applicable)
5. Bidirectional vs unidirectional linking
{f"6. Regional variant handling (same language, different regions)" if is_regional_variant else ""}

Considerations:
- User intent (global vs regional content)
- Search engine crawl efficiency
- Content parity (all languages have complete content?)
- URL structure (subdirectory, subdomain, ccTLD)

Format as JSON:
[
  {{
    "source_url": "{source_url}",
    "target_language": "es",
    "target_url": "{source_url.replace('/en/', '/es/')}",
    "relationship_type": "translation",
    "config_method": "tag"
  }}
]"""

            response = await self.llm.agenerate_text(
                prompt,
                model="claude-opus-4-8",
                max_tokens=2000,
            )

            hreflang_links = self._parse_hreflang_links(response)
            return hreflang_links

        except Exception as exc:
            logger.error("Hreflang strategy generation failed: %s", exc)
            raise

    async def analyze_multilingual_seo(
        self,
        primary_language: str,
        available_languages: list[dict[str, str]],
        translated_content_count: dict[str, int],
        regional_targets: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Analyze multilingual SEO setup and identify gaps."""
        try:
            lang_summary = "\n".join(
                f"- {lang['code']}: {translated_content_count.get(lang['code'], 0)} pages translated"
                for lang in available_languages
            )

            region_summary = "\n".join(
                f"- {r.get('region_code')}: Priority {r.get('priority')}"
                for r in regional_targets[:10]
            )

            prompt = f"""Analyze multilingual SEO setup and identify optimization opportunities.

Primary Language: {primary_language}
Available Languages/Regions:
{lang_summary}

Regional Targets:
{region_summary}

Evaluate:
1. Content completeness across languages (% translated)
2. Translation quality (cultural adaptation vs literal)
3. Hreflang implementation status
4. Regional keyword targeting effectiveness
5. Gaps and priorities for expansion
6. URL structure best practices
7. Language-specific on-page SEO factors
8. Content parity and consistency

Provide:
- Overall multilingual SEO health score (0-100)
- Top 5 priorities for improvement
- Language-specific recommendations
- Regional expansion opportunities
- Implementation roadmap

Format as JSON:
{{
  "health_score": 65,
  "overall_assessment": "Partially implemented multilingual SEO strategy",
  "priorities": [
    {{
      "priority": 1,
      "area": "hreflang_implementation",
      "recommendation": "Deploy hreflang tags for all language versions",
      "impact": "Critical for language version discovery"
    }}
  ],
  "language_recommendations": {{
    "es": "Expand Spanish content coverage (45% complete)",
    "fr": "Native speaker review for French content"
  }},
  "regional_opportunities": [
    {{
      "region": "US",
      "language": "en",
      "potential": "High-value regional keyword targeting"
    }}
  ],
  "implementation_roadmap": [
    "Phase 1: Deploy hreflang infrastructure",
    "Phase 2: Complete core content translations",
    "Phase 3: Regional content adaptation"
  ]
}}"""

            response = await self.llm.agenerate_text(
                prompt,
                model="claude-opus-4-8",
                max_tokens=2500,
            )

            analysis = self._parse_analysis(response)
            return analysis

        except Exception as exc:
            logger.error("Multilingual SEO analysis failed: %s", exc)
            raise

    async def identify_regional_variants(
        self,
        language_code: str,
        competitor_regions: list[str],
    ) -> list[RegionalVariant]:
        """Identify regions where content variants would be beneficial."""
        try:
            regions_list = ", ".join(competitor_regions[:15])

            prompt = f"""Identify regional content opportunities for {language_code}.

Target regions: {regions_list}

For each region, determine:
1. Regional differences in search behavior
2. Local keywords (vs. generic {language_code} keywords)
3. Content adaptation needs (local examples, regulations, preferences)
4. Competitor landscape in region
5. SEO priority (market size + opportunity)
6. Local content format preferences

Format as JSON:
[
  {{
    "region_code": "US",
    "region_name": "United States",
    "target_keywords": ["keyword for US market"],
    "local_content_needed": true,
    "priority": 9
  }}
]"""

            response = await self.llm.agenerate_text(
                prompt,
                model="claude-opus-4-8",
                max_tokens=2000,
            )

            variants = self._parse_regional_variants(response)
            return variants

        except Exception as exc:
            logger.error("Regional variant identification failed: %s", exc)
            raise

    def _parse_localized_content(self, response: str, source_url: str) -> LocalizedContent:
        """Parse localized content from Claude response."""
        try:
            import re

            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if not json_match:
                return LocalizedContent(
                    source_url=source_url,
                    localized_url=source_url,
                    title="",
                    description="",
                    content="",
                    keywords=[],
                )

            data = json.loads(json_match.group())

            return LocalizedContent(
                source_url=source_url,
                localized_url=source_url,  # Would be updated with language path
                title=data.get("title", ""),
                description=data.get("description", ""),
                content=data.get("content", ""),
                keywords=data.get("keywords", []),
                needs_review=data.get("needs_review", False),
            )

        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Failed to parse localized content: %s", exc)
            return LocalizedContent(
                source_url=source_url,
                localized_url=source_url,
                title="",
                description="",
                content="",
                keywords=[],
            )

    def _parse_hreflang_links(self, response: str) -> list[HreflangLink]:
        """Parse hreflang links from Claude response."""
        links = []
        try:
            import re

            json_match = re.search(r"\[.*\]", response, re.DOTALL)
            if not json_match:
                return []

            data = json.loads(json_match.group())

            for item in data[:50]:
                link = HreflangLink(
                    source_url=item.get("source_url", ""),
                    target_url=item.get("target_url", ""),
                    target_language=item.get("target_language", ""),
                    relationship_type=item.get("relationship_type", "translation"),
                )
                links.append(link)

        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Failed to parse hreflang links: %s", exc)

        return links

    def _parse_regional_variants(self, response: str) -> list[RegionalVariant]:
        """Parse regional variants from Claude response."""
        variants = []
        try:
            import re

            json_match = re.search(r"\[.*\]", response, re.DOTALL)
            if not json_match:
                return []

            data = json.loads(json_match.group())

            for item in data[:20]:
                variant = RegionalVariant(
                    region_code=item.get("region_code", ""),
                    region_name=item.get("region_name", ""),
                    target_keywords=item.get("target_keywords", []),
                    local_content_needed=item.get("local_content_needed", False),
                    priority=item.get("priority", 5),
                )
                variants.append(variant)

        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Failed to parse regional variants: %s", exc)

        return variants

    def _parse_analysis(self, response: str) -> dict:
        """Parse multilingual SEO analysis from Claude response."""
        try:
            import re

            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if not json_match:
                return {}

            return json.loads(json_match.group())

        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Failed to parse analysis: %s", exc)
            return {}
