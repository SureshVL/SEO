"""Multilingual SEO service for content translation, localization, and hreflang management."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable
from uuid import UUID

from app.core.pgrest import q
from app.agents.multilingual_agent import (
    MultilingualAgent,
    LocalizedContent,
    HreflangLink,
)

logger = logging.getLogger("omnirank.multilingual")


class MultilingualService:
    """Manages multilingual SEO strategies and content localization workflows."""

    def __init__(self):
        self.agent = MultilingualAgent()

    def add_language(
        self,
        project_id: UUID,
        language_code: str,
        region_code: str | None,
        display_name: str,
        is_default: bool = False,
        db_fn: Callable | None = None,
    ) -> dict[str, Any]:
        """Add a new language/region to the project."""
        if not db_fn:
            return {}

        try:
            result = db_fn(
                "post",
                "languages",
                {
                    "project_id": str(project_id),
                    "language_code": language_code,
                    "region_code": region_code,
                    "display_name": display_name,
                    "is_default": is_default,
                    "is_enabled": True,
                },
            )

            logger.info("Added language %s for project %s", language_code, project_id)
            return {
                "status": "added",
                "language_code": language_code,
                "region_code": region_code,
            }

        except Exception as exc:
            logger.error("Failed to add language: %s", exc)
            raise

    def get_languages(
        self,
        project_id: UUID,
        db_fn: Callable | None = None,
    ) -> list[dict[str, Any]]:
        """Get all languages for a project."""
        if not db_fn:
            return []

        try:
            result = db_fn("get", "languages", params=f"project_id=eq.{project_id}&is_enabled=eq.true")
            return result if isinstance(result, list) else [result] if result else []

        except Exception as exc:
            logger.warning("Failed to fetch languages: %s", exc)
            return []

    async def localize_content(
        self,
        project_id: UUID,
        source_url: str,
        source_content: str,
        source_title: str,
        source_keywords: list[str],
        target_language_id: int,
        target_region: str | None = None,
        db_fn: Callable | None = None,
    ) -> dict[str, Any]:
        """Translate and localize content for a target language."""
        if not db_fn:
            return {}

        try:
            # Get target language details
            lang_result = db_fn("get", "languages", params=f"id=eq.{target_language_id}")
            language_data = lang_result if isinstance(lang_result, list) else [lang_result] if lang_result else []

            if not language_data:
                raise ValueError("Language not found")

            lang = language_data[0]
            target_language = lang.get("language_code", "")

            # Generate localized content
            localized = await self.agent.localize_content(
                source_url,
                source_content,
                source_title,
                source_keywords,
                target_language,
                target_region,
            )

            # Store localized content
            lang_segment = f"{target_language}-{target_region}" if target_region else target_language
            if "/en/" in source_url:
                localized_url = source_url.replace("/en/", f"/{lang_segment}/")
            elif source_url.startswith("/"):
                localized_url = f"/{lang_segment}{source_url}"
            else:
                localized_url = f"/{lang_segment}/{source_url.lstrip('/')}"

            row = {
                    "project_id": str(project_id),
                    "language_id": target_language_id,
                    "source_url": source_url,
                    "localized_url": localized_url,
                    "title": localized.title,
                    "description": localized.description,
                    "content_markdown": localized.content,
                    "keywords": localized.keywords,
                    "translation_status": "completed" if not localized.needs_review else "needs_review",
                    "translation_model": "claude",
                    "needs_human_review": localized.needs_review,
                    "translated_by": "claude-opus-4-8",
            }
            existing = db_fn(
                "get", "localized_content",
                params=f"project_id=eq.{project_id}&language_id=eq.{target_language_id}"
                       f"&source_url=eq.{q(source_url)}&select=id",
            )
            existing = existing if isinstance(existing, list) else [existing] if existing else []
            if existing:
                db_fn("patch", f"localized_content?id=eq.{existing[0]['id']}", row)
            else:
                db_fn("post", "localized_content", row)

            logger.info("Localized content for %s to %s", source_url, target_language)

            return {
                "status": "localized",
                "source_url": source_url,
                "localized_url": localized_url,
                "language": target_language,
                "needs_review": localized.needs_review,
            }

        except Exception as exc:
            logger.error("Content localization failed: %s", exc)
            raise

    async def generate_hreflang_strategy(
        self,
        project_id: UUID,
        source_url: str,
        db_fn: Callable | None = None,
    ) -> list[dict[str, Any]]:
        """Generate and store hreflang strategy."""
        if not db_fn:
            return []

        try:
            # Get available languages
            languages = self.get_languages(project_id, db_fn)
            if not languages:
                raise ValueError("No languages configured")

            available_langs = [
                {"code": lang.get("language_code"), "name": lang.get("display_name")}
                for lang in languages
            ]

            # Generate hreflang links
            hreflang_links = await self.agent.generate_hreflang_strategy(
                source_url,
                available_langs,
            )

            # Map language code -> id so we store a valid foreign key
            lang_id_by_code = {
                lang.get("language_code"): lang.get("id") for lang in languages
            }

            # Store hreflang config
            stored = []
            for link in hreflang_links:
                target_lang_id = lang_id_by_code.get(link.target_language)
                if not target_lang_id:
                    logger.warning("Skipping hreflang for unknown language: %s", link.target_language)
                    continue
                try:
                    result = db_fn(
                        "post",
                        "hreflang_config",
                        {
                            "project_id": str(project_id),
                            "source_url": link.source_url,
                            "target_url": link.target_url,
                            "target_language_id": target_lang_id,
                            "relationship_type": link.relationship_type,
                            "is_configured": False,
                            "config_method": "tag",
                        },
                    )

                    stored.append({
                        "source_url": link.source_url,
                        "target_url": link.target_url,
                        "target_language": link.target_language,
                    })

                except Exception as e:
                    logger.warning("Failed to store hreflang: %s", e)

            logger.info("Created %d hreflang links for %s", len(stored), source_url)
            return stored

        except Exception as exc:
            logger.error("Hreflang strategy generation failed: %s", exc)
            raise

    async def analyze_multilingual_setup(
        self,
        project_id: UUID,
        db_fn: Callable | None = None,
    ) -> dict[str, Any]:
        """Analyze multilingual SEO setup and identify gaps."""
        if not db_fn:
            return {}

        try:
            # Get languages
            languages = self.get_languages(project_id, db_fn)
            if not languages:
                return {
                    "health_score": 0,
                    "overall_assessment": "No languages configured",
                    "message": "Configure languages first",
                }

            # Get translation progress
            translated_result = db_fn(
                "get",
                "localized_content",
                params=f"project_id=eq.{project_id}",
            )
            translated_list = translated_result if isinstance(translated_result, list) else [translated_result] if translated_result else []

            translated_by_lang: dict[str, int] = {}
            for item in translated_list:
                lang_id = item.get("language_id")
                translated_by_lang[str(lang_id)] = translated_by_lang.get(str(lang_id), 0) + 1

            # Get regional targets
            regions_result = db_fn("get", "region_targeting", params=f"project_id=eq.{project_id}")
            regions = regions_result if isinstance(regions_result, list) else [regions_result] if regions_result else []

            # Analyze
            primary_lang = next((l for l in languages if l.get("is_default")), languages[0]) if languages else None
            primary_language = primary_lang.get("language_code") if primary_lang else "en"

            analysis = await self.agent.analyze_multilingual_seo(
                primary_language,
                [{"code": l.get("language_code"), "name": l.get("display_name")} for l in languages],
                translated_by_lang,
                regions,
            )

            return analysis

        except Exception as exc:
            logger.error("Multilingual SEO analysis failed: %s", exc)
            raise

    async def identify_regional_opportunities(
        self,
        project_id: UUID,
        language_id: int,
        competitor_regions: list[str],
        db_fn: Callable | None = None,
    ) -> list[dict[str, Any]]:
        """Identify regional content opportunities."""
        if not db_fn:
            return []

        try:
            # Get language
            lang_result = db_fn("get", "languages", params=f"id=eq.{language_id}")
            language_data = lang_result if isinstance(lang_result, list) else [lang_result] if lang_result else []

            if not language_data:
                return []

            language_code = language_data[0].get("language_code", "")

            # Identify variants
            variants = await self.agent.identify_regional_variants(
                language_code,
                competitor_regions,
            )

            # Store regional targeting
            stored = []
            for variant in variants:
                try:
                    result = db_fn(
                        "post",
                        "region_targeting",
                        {
                            "project_id": str(project_id),
                            "language_id": language_id,
                            "region_code": variant.region_code,
                            "region_name": variant.region_name,
                            "target_keywords": variant.target_keywords,
                            "local_content_needed": variant.local_content_needed,
                            "seo_priority": variant.priority,
                        },
                    )

                    stored.append({
                        "region_code": variant.region_code,
                        "region_name": variant.region_name,
                        "target_keywords": variant.target_keywords,
                        "local_content_needed": variant.local_content_needed,
                        "priority": variant.priority,
                    })

                except Exception as e:
                    logger.warning("Failed to store regional targeting: %s", e)

            logger.info("Identified %d regional opportunities", len(stored))
            return stored

        except Exception as exc:
            logger.error("Regional opportunity identification failed: %s", exc)
            raise

    def get_localized_content(
        self,
        project_id: UUID,
        language_id: int | None = None,
        source_url: str | None = None,
        db_fn: Callable | None = None,
    ) -> list[dict[str, Any]]:
        """Get localized content."""
        if not db_fn:
            return []

        try:
            params = f"project_id=eq.{project_id}"
            if language_id:
                params += f"&language_id=eq.{language_id}"
            if source_url:
                params += f"&source_url=eq.{q(source_url)}"
            params += "&order=created_at.desc"

            result = db_fn("get", "localized_content", params=params)
            return result if isinstance(result, list) else [result] if result else []

        except Exception as exc:
            logger.warning("Failed to fetch localized content: %s", exc)
            return []

    def get_hreflang_config(
        self,
        project_id: UUID,
        source_url: str | None = None,
        db_fn: Callable | None = None,
    ) -> list[dict[str, Any]]:
        """Get hreflang configuration."""
        if not db_fn:
            return []

        try:
            params = f"project_id=eq.{project_id}"
            if source_url:
                params += f"&source_url=eq.{q(source_url)}"

            result = db_fn("get", "hreflang_config", params=params)
            return result if isinstance(result, list) else [result] if result else []

        except Exception as exc:
            logger.warning("Failed to fetch hreflang config: %s", exc)
            return []

    def get_regional_targeting(
        self,
        project_id: UUID,
        language_id: int | None = None,
        db_fn: Callable | None = None,
    ) -> list[dict[str, Any]]:
        """Get regional targeting configuration."""
        if not db_fn:
            return []

        try:
            params = f"project_id=eq.{project_id}&order=seo_priority.desc"
            if language_id:
                params += f"&language_id=eq.{language_id}"

            result = db_fn("get", "region_targeting", params=params)
            return result if isinstance(result, list) else [result] if result else []

        except Exception as exc:
            logger.warning("Failed to fetch regional targeting: %s", exc)
            return []
