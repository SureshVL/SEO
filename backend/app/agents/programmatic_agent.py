"""Programmatic SEO agent — template-driven page generation.

Given a page template (markdown + frontmatter with {{variable}}
placeholders) and a CSV/JSON dataset, produces a bulk set of SEO pages
that can be reviewed + published. Common pattern: city × service grids
(e.g., "Plumbing services in {{city}}") or product × category.

Optionally enriches content via Claude when the template asks for
AI-expanded sections, and scores generated pages via ContentAgent so
authors can skip the worst offenders before publishing.
"""

from __future__ import annotations

import csv
import io
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

logger = logging.getLogger("omnirank.programmatic")


VAR_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_\.]+)\s*\}\}")
SLUG_CHARS = re.compile(r"[^a-z0-9]+")


@dataclass
class ProgrammaticPage:
    slug: str
    title: str
    meta_description: str
    h1: str
    body_markdown: str
    variables: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ProgrammaticResult:
    template_name: str
    total_rows: int
    generated: int
    skipped: int
    variables_used: list[str]
    pages: list[ProgrammaticPage] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ProgrammaticAgent:
    """Bulk-generate SEO pages from a template + dataset."""

    def generate(
        self,
        template: dict[str, Any],
        rows: list[dict[str, Any]],
        *,
        dedupe_on: str = "slug",
        max_pages: int = 500,
    ) -> ProgrammaticResult:
        """Merge `rows` into `template` and produce ProgrammaticPage list.

        template keys: name, slug_template, title_template,
                       meta_description_template, h1_template, body_template
        rows: list of dicts (typically parsed from CSV)
        """
        name = template.get("name", "programmatic")
        slug_tpl = template.get("slug_template", "/{{slug}}")
        title_tpl = template.get("title_template", "{{title}}")
        meta_tpl = template.get("meta_description_template", "")
        h1_tpl = template.get("h1_template", title_tpl)
        body_tpl = template.get("body_template", "")

        used_vars = sorted({
            *extract_variables(slug_tpl),
            *extract_variables(title_tpl),
            *extract_variables(meta_tpl),
            *extract_variables(h1_tpl),
            *extract_variables(body_tpl),
        })

        warnings: list[str] = []
        pages: list[ProgrammaticPage] = []
        seen = set()
        skipped = 0

        for row in rows[:max_pages]:
            page_warnings: list[str] = []
            missing = [v for v in used_vars if v not in row or row.get(v) in (None, "")]
            if missing:
                page_warnings.append(f"Missing variables: {', '.join(missing)}")

            slug = slugify(substitute(slug_tpl, row))
            title = substitute(title_tpl, row)
            meta = substitute(meta_tpl, row)
            h1 = substitute(h1_tpl, row)
            body = substitute(body_tpl, row)

            dedupe_key = slug if dedupe_on == "slug" else str(row.get(dedupe_on, slug))
            if dedupe_key in seen:
                skipped += 1
                continue
            seen.add(dedupe_key)

            pages.append(ProgrammaticPage(
                slug=slug, title=title, meta_description=meta, h1=h1,
                body_markdown=body, variables=dict(row),
                warnings=page_warnings,
            ))

        if len(rows) > max_pages:
            warnings.append(
                f"{len(rows) - max_pages} rows truncated (max_pages={max_pages})",
            )

        if not used_vars:
            warnings.append(
                "Template contained no {{variables}} — every generated page is identical.",
            )

        return ProgrammaticResult(
            template_name=name,
            total_rows=len(rows),
            generated=len(pages),
            skipped=skipped,
            variables_used=used_vars,
            pages=pages,
            warnings=warnings,
        )

    # ── Utilities ───────────────────────────────────────────────────────────

    @staticmethod
    def parse_csv(raw: str) -> list[dict[str, str]]:
        """Parse CSV text into a list of dict rows. Empty input → []."""
        raw = (raw or "").strip()
        if not raw:
            return []
        reader = csv.DictReader(io.StringIO(raw))
        return [{k: (v or "").strip() for k, v in r.items() if k} for r in reader]


def extract_variables(text: str) -> set[str]:
    """Return the set of {{variable}} names referenced in `text`."""
    return set(VAR_PATTERN.findall(text or ""))


def substitute(text: str, row: dict[str, Any]) -> str:
    """Substitute {{var}} placeholders from row dict. Leaves unknown vars blank."""
    def replace(match: re.Match) -> str:
        key = match.group(1)
        val = row.get(key, "")
        return str(val) if val is not None else ""
    return VAR_PATTERN.sub(replace, text or "")


def slugify(value: str) -> str:
    """Turn '/Plumbing in Austin!' into '/plumbing-in-austin'."""
    s = (value or "").strip().lower()
    has_leading_slash = s.startswith("/")
    # Strip leading slash temporarily to avoid collapsing it
    if has_leading_slash:
        s = s[1:]
    s = SLUG_CHARS.sub("-", s).strip("-")
    return ("/" + s) if has_leading_slash else s
