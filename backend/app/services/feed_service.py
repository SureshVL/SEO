"""Product-feed intelligence: SKU-scale listing optimization for e-commerce.

Imports a product catalog (CSV or Google Merchant XML feed), finds listing
issues deterministically at scale, AI-optimizes titles/descriptions within
the org's plan budget, and exports a Google Merchant supplemental feed.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import re  # noqa: F401 - used in optimize_products
from datetime import datetime, timezone
from typing import Any, Callable
from xml.etree import ElementTree

import httpx

logger = logging.getLogger("omnirank.feeds")

IMPORT_CAP = 5000  # products stored per feed (analysis stays cheap)

PROMO_WORDS = (
    "free shipping", "best price", "cheap", "sale!!", "!!!", "buy now",
    "limited time", "% off", "discount", "lowest price",
)

# AI optimization budgets per plan (SKUs per run). Trials stay small.
FEED_SKU_BUDGETS = {
    "trial": 10,
    "starter": 100,
    "growth": 1000,
    "agency": 10000,
    "enterprise": 50000,
}


def feed_sku_budget_for(plan: str | None, plan_status: str | None) -> int:
    if plan_status != "active":
        return FEED_SKU_BUDGETS["trial"]
    return FEED_SKU_BUDGETS.get(plan or "", FEED_SKU_BUDGETS["trial"])


# ── Parsing ──────────────────────────────────────────────────────────

CSV_FIELD_ALIASES = {
    "product_key": ("id", "sku", "product id", "item id", "g:id"),
    "title": ("title", "name", "product name", "g:title"),
    "description": ("description", "g:description", "body (html)"),
    "brand": ("brand", "vendor", "g:brand", "manufacturer"),
    "category": ("category", "product category", "g:google_product_category", "product_type", "g:product_type", "type"),
    "price": ("price", "g:price", "variant price"),
    "link": ("link", "url", "g:link", "handle"),
    "availability": ("availability", "g:availability", "stock", "in stock"),
}


def _pick(row: dict[str, str], field: str) -> str:
    lowered = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
    for alias in CSV_FIELD_ALIASES[field]:
        if alias in lowered and lowered[alias]:
            return lowered[alias]
    return ""


def parse_csv_feed(text: str) -> list[dict[str, str]]:
    """Parse a CSV product feed (Google Merchant, Shopify export, generic)."""
    # sniff delimiter (comma or tab)
    delimiter = "\t" if text[:2000].count("\t") > text[:2000].count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    products = []
    truncated = False
    for i, row in enumerate(reader):
        if i >= IMPORT_CAP:
            truncated = True
            break
        product = {f: _pick(row, f) for f in CSV_FIELD_ALIASES}
        if not product["product_key"]:
            product["product_key"] = f"row-{i + 1}"
        if product["title"] or product["link"]:
            products.append(product)
    return products, truncated


def parse_xml_feed(content: bytes):
    """Parse a Google Merchant RSS/Atom XML feed."""
    from app.core.ssrf import safe_parse_xml
    root = safe_parse_xml(content)
    g = "{http://base.google.com/ns/1.0}"
    atom = "{http://www.w3.org/2005/Atom}"

    def text_of(item, *names) -> str:
        for name in names:
            el = item.find(name)
            if el is not None and el.text:
                return el.text.strip()
        return ""

    def link_of(item) -> str:
        text = text_of(item, f"{g}link", "link", f"{atom}link")
        if text:
            return text
        el = item.find(f"{atom}link") or item.find("link")
        return (el.get("href", "") if el is not None else "").strip()

    items = root.findall(".//item") or root.findall(f".//{atom}entry")
    products = []
    truncated = False
    for i, item in enumerate(items):
        if i >= IMPORT_CAP:
            truncated = True
            break
        product = {
            "product_key": text_of(item, f"{g}id", "id", f"{atom}id") or f"item-{i + 1}",
            "title": text_of(item, f"{g}title", "title", f"{atom}title"),
            "description": text_of(item, f"{g}description", "description", f"{atom}summary"),
            "brand": text_of(item, f"{g}brand"),
            "category": text_of(item, f"{g}google_product_category", f"{g}product_type"),
            "price": text_of(item, f"{g}price"),
            "link": link_of(item),
            "availability": text_of(item, f"{g}availability"),
        }
        if product["title"] or product["link"]:
            products.append(product)
    return products, truncated


# ── Deterministic listing analysis ───────────────────────────────────

def analyze_product(p: dict[str, str], duplicate_titles: set[str]) -> list[dict[str, str]]:
    """Google Shopping / marketplace listing checks. No LLM needed."""
    issues: list[dict[str, str]] = []
    title = p.get("title", "") or ""
    desc = p.get("description", "") or ""
    brand = p.get("brand", "") or ""

    def add(issue_type, severity, detail):
        issues.append({"type": issue_type, "severity": severity, "detail": detail})

    if not title:
        add("missing_title", "critical", "Product has no title.")
    else:
        if len(title) < 20:
            add("title_too_short", "warning", f"Title is {len(title)} chars; aim for 50-150 with brand + product type + attributes.")
        if len(title) > 150:
            add("title_too_long", "warning", f"Title is {len(title)} chars; Google truncates after ~150.")
        if title.isupper():
            add("title_all_caps", "warning", "All-caps titles are penalized in Shopping listings.")
        lowered = title.lower()
        for promo in PROMO_WORDS:
            if promo in lowered:
                add("promo_text_in_title", "warning", f"Promotional text ('{promo}') violates Google Shopping title policy.")
                break
        if title.lower() in duplicate_titles:
            add("duplicate_title", "warning", "Same title as other products; add distinguishing attributes (size, color, model).")
        if brand and brand.lower() not in lowered:
            add("brand_missing_from_title", "info", f"Brand '{brand}' not in the title; leading with brand improves CTR.")

    if not desc:
        add("missing_description", "critical", "Product has no description.")
    elif len(desc) < 100:
        add("description_too_short", "warning", f"Description is {len(desc)} chars; aim for 300-1000 with benefits and specs.")

    if not brand:
        add("missing_brand", "warning", "No brand field; required for most Shopping categories.")
    if not p.get("price"):
        add("missing_price", "critical", "No price field.")
    if not p.get("link"):
        add("missing_link", "critical", "No product URL.")
    if not p.get("availability"):
        add("missing_availability", "info", "No availability field (in stock / out of stock).")

    return issues


def _issues_of(p: dict[str, Any]) -> list[dict[str, Any]]:
    """feed_products.issues may arrive as native jsonb (list) or legacy string."""
    raw = p.get("issues")
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return []
    return []


class FeedService:
    """Import, analyze, optimize, and export product feeds."""

    async def import_feed(
        self,
        project_id: str,
        name: str,
        source_url: str = "",
        csv_text: str = "",
        db_fn: Callable | None = None,
    ) -> dict[str, Any]:
        """Import from a feed URL (XML/CSV) or pasted CSV text, then analyze."""
        if source_url:
            from app.core.ssrf import guarded_async_client, validate_public_url, read_capped
            validate_public_url(source_url)  # raises SSRFError on private/internal hosts
            async with guarded_async_client(timeout=60, follow_redirects=True) as client:
                async with client.stream("GET", source_url) as resp:
                    resp.raise_for_status()
                    body = await read_capped(resp)
            stripped = body.lstrip()[:200]
            if stripped.startswith(b"<"):
                products, truncated = parse_xml_feed(body)
            else:
                products, truncated = parse_csv_feed(body.decode("utf-8", errors="replace"))
            source_type = "url"
        elif csv_text:
            products, truncated = parse_csv_feed(csv_text)
            source_type = "csv"
        else:
            raise ValueError("Provide a feed URL or CSV content")

        if not products:
            raise ValueError("No products found in the feed")

        # duplicate-title index across the whole feed
        title_counts: dict[str, int] = {}
        for p in products:
            t = (p.get("title") or "").lower()
            if t:
                title_counts[t] = title_counts.get(t, 0) + 1
        duplicates = {t for t, c in title_counts.items() if c > 1}

        total_issues = 0
        analyzed = []
        for p in products:
            issues = analyze_product(p, duplicates)
            total_issues += len(issues)
            analyzed.append((p, issues))

        feed_rows = db_fn("post", "product_feeds", {
            "project_id": project_id,
            "name": name or (source_url.split("/")[-1] if source_url else "Pasted CSV"),
            "source_type": source_type,
            "source_url": source_url,
            "product_count": len(products),
            "issue_count": total_issues,
            "truncated": truncated,
            "status": "ready",
            "last_imported": datetime.now(timezone.utc).isoformat(),
        })
        feed = feed_rows[0] if isinstance(feed_rows, list) and feed_rows else feed_rows
        feed_id = feed["id"]

        def _store_all() -> int:
            count = 0
            rows = [
                {
                    "feed_id": feed_id,
                    "project_id": project_id,
                    "product_key": p["product_key"][:255],
                    "title": (p.get("title") or "")[:1000],
                    "description": p.get("description") or "",
                    "brand": (p.get("brand") or "")[:255],
                    "category": (p.get("category") or "")[:500],
                    "price": (p.get("price") or "")[:100],
                    "link": (p.get("link") or "")[:1000],
                    "availability": (p.get("availability") or "")[:50],
                    "issues": issues,
                    "issue_count": len(issues),
                }
                for p, issues in analyzed
            ]
            # bulk insert in chunks (PostgREST accepts arrays) - one call per
            # 500 products instead of one per product, off the event loop
            for start in range(0, len(rows), 500):
                chunk = rows[start:start + 500]
                try:
                    db_fn("post", "feed_products", chunk)
                    count += len(chunk)
                except Exception as exc:
                    logger.warning("Bulk insert failed (%d rows): %s - retrying row-by-row", len(chunk), exc)
                    for row in chunk:
                        try:
                            db_fn("post", "feed_products", row)
                            count += 1
                        except Exception as row_exc:
                            logger.warning("Could not store product %s: %s", row.get("product_key"), row_exc)
            return count

        import asyncio
        stored = await asyncio.to_thread(_store_all)

        logger.info("Imported feed %s: %d products, %d issues", feed_id, stored, total_issues)
        return {
            "feed_id": feed_id,
            "product_count": len(products),
            "stored": stored,
            "issue_count": total_issues,
            "truncated": truncated,
        }

    def get_feeds(self, project_id: str, db_fn: Callable) -> list[dict[str, Any]]:
        rows = db_fn("get", "product_feeds", params=f"project_id=eq.{project_id}&order=created_at.desc")
        return rows if isinstance(rows, list) else [rows] if rows else []

    def get_products(
        self, feed_id: int, db_fn: Callable,
        only_issues: bool = False, limit: int = 100, offset: int = 0,
        optimization_status: str = "", project_id: str = "",
    ) -> list[dict[str, Any]]:
        params = f"feed_id=eq.{feed_id}&order=issue_count.desc&limit={limit}&offset={offset}"
        if project_id:
            params += f"&project_id=eq.{project_id}"
        if only_issues:
            params += "&issue_count=gt.0"
        if optimization_status:
            params += f"&optimization_status=eq.{optimization_status}"
        rows = db_fn("get", "feed_products", params=params)
        return rows if isinstance(rows, list) else [rows] if rows else []

    async def optimize_products(
        self,
        feed_id: int,
        sku_budget: int,
        db_fn: Callable,
    ) -> dict[str, Any]:
        """AI-rewrite titles/descriptions for the worst products, within budget."""
        from app.clients.llm import llm_client

        import asyncio as _aio

        # fetch PENDING products only, so repeat runs keep making progress
        pending = (await _aio.to_thread(
            self.get_products, feed_id, db_fn, True,
            min(sku_budget, 500), 0, "pending",
        ))[:sku_budget]
        if not pending:
            return {"optimized": 0, "message": "No pending products with issues"}

        optimized = 0
        for batch_start in range(0, len(pending), 10):
            batch = pending[batch_start:batch_start + 10]
            listing = "\n".join(
                f"- id={p['id']} | title: {p.get('title') or '(none)'} | brand: {p.get('brand') or '?'} "
                f"| category: {p.get('category') or '?'} | issues: {', '.join(i['type'] for i in json.loads(p.get('issues') or '[]'))}"
                for p in batch
            )
            prompt = f"""Rewrite these e-commerce product listings per Google Shopping best practices.

Title format: Brand + Product Type + Key Attributes (color/size/material/model). 50-150 chars, no promo text, no all-caps.
Description: 300-600 chars, benefits first, then specs. Plain text.

Products:
{listing}

Return ONLY a JSON array:
[{{"id": 123, "title": "...", "description": "..."}}]"""

            try:
                response = await llm_client.agenerate_text(prompt, max_tokens=2500, temperature=0.4)
                match = re.search(r"\[.*\]", response, re.DOTALL)
                if not match:
                    continue
                rewrites = json.loads(match.group())
            except Exception as exc:
                logger.error("Feed optimization batch failed: %s", exc)
                continue

            batch_ids = {p["id"] for p in batch}
            for rw in rewrites:
                pid = rw.get("id")
                new_title = (rw.get("title") or "").strip()
                # only accept ids that were actually in this batch - LLM output
                # must never be able to address other rows
                if pid not in batch_ids or not new_title:
                    continue
                try:
                    import asyncio as _aio
                    await _aio.to_thread(
                        db_fn, "patch",
                        f"feed_products?id=eq.{pid}&feed_id=eq.{feed_id}",
                        {
                            "optimized_title": new_title[:1000],
                            "optimized_description": (rw.get("description") or "").strip(),
                            "optimization_status": "optimized",
                        },
                    )
                    optimized += 1
                except Exception as exc:
                    logger.warning("Could not store optimization for %s: %s", pid, exc)

        try:
            all_optimized = db_fn(
                "get", "feed_products",
                params=f"feed_id=eq.{feed_id}&optimization_status=eq.optimized&select=id&limit=10000",
            )
            total = len(all_optimized) if isinstance(all_optimized, list) else 0
            db_fn("patch", f"product_feeds?id=eq.{feed_id}", {"optimized_count": total})
        except Exception:
            pass

        return {"optimized": optimized, "budget": sku_budget, "candidates": len(pending)}

    def export_supplemental_feed(self, feed_id: int, db_fn: Callable) -> str:
        """CSV supplemental feed (id, title, description) for Google Merchant Center."""
        rows = db_fn(
            "get", "feed_products",
            params=f"feed_id=eq.{feed_id}&optimization_status=eq.optimized&limit=10000",
        )
        rows = rows if isinstance(rows, list) else [rows] if rows else []

        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["id", "title", "description"])
        for r in rows:
            writer.writerow([
                r.get("product_key", ""),
                r.get("optimized_title") or r.get("title") or "",
                r.get("optimized_description") or r.get("description") or "",
            ])
        return out.getvalue()
