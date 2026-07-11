"""AI Visibility (GEO) Agent.

Tracks whether a target domain shows up in:
1. Google AI Overview citations (parsed from live SERP)
2. Google AI Mode answers (new conversational SERP)
3. LLM responses from ChatGPT / Perplexity / Gemini (DataForSEO AI-Optimization API)

Produces a per-keyword and aggregate visibility score for the dashboard.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from app.clients.dataforseo_client import DataForSEOClient

logger = logging.getLogger("omnirank.ai_visibility")

DEFAULT_ENGINES = ("chat_gpt", "perplexity", "gemini")


@dataclass
class KeywordVisibility:
    keyword: str
    ai_overview_present: bool = False
    ai_overview_cited: bool = False
    ai_overview_position: int | None = None
    ai_overview_snippet: str = ""
    ai_overview_citations: list[dict[str, Any]] = field(default_factory=list)
    ai_mode_present: bool = False
    ai_mode_cited: bool = False
    ai_mode_snippet: str = ""
    llm_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    visibility_score: float = 0.0


@dataclass
class AIVisibilityReport:
    domain: str
    total_keywords: int
    engines: list[str]
    overall_score: float
    ai_overview_coverage: float  # % of keywords that trigger AI overview at all
    ai_overview_citation_rate: float  # % cited when overview present
    llm_mention_rate: dict[str, float] = field(default_factory=dict)
    keywords: list[KeywordVisibility] = field(default_factory=list)


class AIVisibilityAgent:
    """Checks AI-surface visibility for a domain across a keyword list."""

    def __init__(self, dataforseo_client: DataForSEOClient):
        self.dfs = dataforseo_client

    @property
    def enabled(self) -> bool:
        return bool(self.dfs and self.dfs.enabled)

    @staticmethod
    def _domain_mentioned(text: str, domain: str) -> bool:
        if not text or not domain:
            return False
        target = domain.lower().strip().replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
        if not target:
            return False
        # Match bare domain or any URL containing it (case-insensitive, word-ish boundary)
        return bool(re.search(rf"(^|\W){re.escape(target)}(\W|$)", text.lower()))

    @staticmethod
    def _domain_in_refs(refs: list[dict[str, Any]], domain: str) -> int | None:
        """Return 1-based position of domain in references, or None."""
        if not domain:
            return None
        target = DataForSEOClient._extract_domain(domain)
        for idx, ref in enumerate(refs or [], 1):
            if ref.get("domain") == target:
                return idx
        return None

    def check_keyword(
        self,
        keyword: str,
        domain: str,
        location_code: int = 2356,
        language_code: str = "en",
        engines: tuple[str, ...] = DEFAULT_ENGINES,
        include_ai_mode: bool = False,
        prompt_template: str = "What are the best {keyword}? List specific providers with their websites.",
    ) -> KeywordVisibility:
        kv = KeywordVisibility(keyword=keyword)

        # 1. Google AI Overview (parsed from normal SERP)
        try:
            overview = self.dfs.ai_overview_for_keyword(
                keyword, domain=domain,
                location_code=location_code, language_code=language_code,
            )
            kv.ai_overview_present = overview.get("present", False)
            kv.ai_overview_cited = overview.get("domain_cited", False)
            kv.ai_overview_position = overview.get("domain_position")
            kv.ai_overview_snippet = overview.get("snippet", "")
            kv.ai_overview_citations = overview.get("citations", []) or []
        except Exception as exc:
            logger.warning("AI overview check failed for %s: %s", keyword, exc)

        # 2. Google AI Mode (opt-in; separate endpoint, may not be available in all accounts)
        if include_ai_mode:
            try:
                ai_mode = self.dfs.ai_mode_serp(keyword, location_code, language_code)
                kv.ai_mode_present = ai_mode.get("present", False)
                kv.ai_mode_snippet = ai_mode.get("answer", "")
                pos = self._domain_in_refs(ai_mode.get("references", []), domain)
                kv.ai_mode_cited = pos is not None or self._domain_mentioned(kv.ai_mode_snippet, domain)
            except Exception as exc:
                logger.debug("AI mode check skipped for %s: %s", keyword, exc)

        # 3. LLM engines (ChatGPT / Perplexity / Gemini)
        prompt = prompt_template.format(keyword=keyword)
        for engine in engines:
            try:
                resp = self.dfs.llm_response(prompt, model=engine, language_code=language_code)
                text = resp.get("text", "")
                refs = resp.get("references", []) or []
                ref_position = self._domain_in_refs(refs, domain)
                mentioned_in_text = self._domain_mentioned(text, domain)
                kv.llm_results[engine] = {
                    "mentioned": bool(ref_position) or mentioned_in_text,
                    "citation_position": ref_position,
                    "reference_count": len(refs),
                    "snippet": text[:400],
                    "error": resp.get("error"),
                }
            except Exception as exc:
                logger.warning("LLM check failed (%s, %s): %s", engine, keyword, exc)
                kv.llm_results[engine] = {
                    "mentioned": False,
                    "citation_position": None,
                    "reference_count": 0,
                    "snippet": "",
                    "error": str(exc),
                }

        kv.visibility_score = self._score_keyword(kv, engines)
        return kv

    @staticmethod
    def _score_keyword(kv: KeywordVisibility, engines: tuple[str, ...]) -> float:
        """0-100 score combining AI Overview citation + LLM mention rate.

        Weights:
          40 — cited in Google AI Overview (or 20 if overview present but uncited)
          20 — cited/mentioned in AI Mode answer (if checked)
          40 — avg across LLM engines (full credit for cited, half for text mention)
        """
        score = 0.0
        if kv.ai_overview_cited:
            score += 40
        elif kv.ai_overview_present:
            score += 10

        if kv.ai_mode_cited:
            score += 20
        elif kv.ai_mode_present:
            score += 5

        engine_hits = 0.0
        checked = 0
        for eng in engines:
            res = kv.llm_results.get(eng)
            if not res or res.get("error"):
                continue
            checked += 1
            if res.get("citation_position"):
                engine_hits += 1.0
            elif res.get("mentioned"):
                engine_hits += 0.5
        if checked:
            score += (engine_hits / checked) * 40

        return round(min(score, 100.0), 1)

    def run(
        self,
        keywords: list[str],
        domain: str,
        location_code: int = 2356,
        language_code: str = "en",
        engines: tuple[str, ...] = DEFAULT_ENGINES,
        include_ai_mode: bool = False,
        prompt_template: str = "What are the best {keyword}? List specific providers with their websites.",
    ) -> AIVisibilityReport:
        clean_domain = DataForSEOClient._extract_domain(domain)
        kv_list: list[KeywordVisibility] = []
        for kw in keywords:
            kv_list.append(self.check_keyword(
                kw, domain,
                location_code=location_code,
                language_code=language_code,
                engines=engines,
                include_ai_mode=include_ai_mode,
                prompt_template=prompt_template,
            ))

        total = len(kv_list) or 1
        overview_present = sum(1 for k in kv_list if k.ai_overview_present)
        overview_cited = sum(1 for k in kv_list if k.ai_overview_cited)

        llm_rates: dict[str, float] = {}
        for eng in engines:
            hits = sum(1 for k in kv_list if (k.llm_results.get(eng, {}).get("mentioned")))
            llm_rates[eng] = round(hits / total * 100, 1)

        overall = round(sum(k.visibility_score for k in kv_list) / total, 1)

        return AIVisibilityReport(
            domain=clean_domain,
            total_keywords=len(kv_list),
            engines=list(engines),
            overall_score=overall,
            ai_overview_coverage=round(overview_present / total * 100, 1),
            ai_overview_citation_rate=round(
                (overview_cited / overview_present * 100) if overview_present else 0, 1
            ),
            llm_mention_rate=llm_rates,
            keywords=kv_list,
        )
