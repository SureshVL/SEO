"""Tests for product-feed intelligence: parsing, analysis, budgets, export."""

import asyncio

from app.services.feed_service import (
    FeedService, parse_csv_feed, parse_xml_feed, analyze_product,
    feed_sku_budget_for, IMPORT_CAP,
)

CSV_TEXT = """id,title,description,brand,price,link,availability
SKU-1,ACME BLUE RUNNING SHOES FREE SHIPPING,,Acme,29.99,https://shop.com/p/1,in stock
SKU-2,Shoes,Short desc,Acme,19.99,https://shop.com/p/2,in stock
SKU-3,Acme Trail Running Shoes - Men's Waterproof Size 42,A great pair of trail shoes with waterproof membrane and grippy soles designed for rocky terrain and long-distance comfort in all weather conditions.,Acme,49.99,https://shop.com/p/3,in stock
SKU-4,Shoes,,,,,
"""

XML_FEED = b"""<?xml version="1.0"?>
<rss xmlns:g="http://base.google.com/ns/1.0"><channel>
<item><g:id>X1</g:id><g:title>Acme Widget Pro 3000</g:title><g:description>Industrial widget.</g:description>
<g:brand>Acme</g:brand><g:price>99 USD</g:price><g:link>https://shop.com/x1</g:link><g:availability>in stock</g:availability></item>
</channel></rss>"""


class TestParsers:
    def test_csv_parses_all_rows(self):
        products, _ = parse_csv_feed(CSV_TEXT)
        assert [p["product_key"] for p in products] == ["SKU-1", "SKU-2", "SKU-3", "SKU-4"]

    def test_csv_alias_headers(self):
        text = "sku,name,vendor,variant price,url\nA1,Nice Product,Brandy,9.99,https://x.com/a1\n"
        products, _ = parse_csv_feed(text)
        assert products[0]["product_key"] == "A1"
        assert products[0]["title"] == "Nice Product"
        assert products[0]["brand"] == "Brandy"

    def test_tsv_delimiter_sniffing(self):
        text = "id\ttitle\tprice\nT1\tTabbed Product\t5.00\n"
        products, _ = parse_csv_feed(text)
        assert products[0]["product_key"] == "T1"

    def test_xml_google_merchant(self):
        products, _ = parse_xml_feed(XML_FEED)
        assert products[0]["product_key"] == "X1"
        assert products[0]["brand"] == "Acme"
        assert products[0]["availability"] == "in stock"


class TestListingAnalyzer:
    def test_promo_and_caps_and_missing_desc(self):
        products, _ = parse_csv_feed(CSV_TEXT)
        issues = {i["type"] for i in analyze_product(products[0], set())}
        assert {"title_all_caps", "promo_text_in_title", "missing_description"} <= issues

    def test_duplicates_and_short_fields(self):
        products, _ = parse_csv_feed(CSV_TEXT)
        issues = {i["type"] for i in analyze_product(products[1], {"shoes"})}
        assert {"duplicate_title", "title_too_short", "description_too_short"} <= issues

    def test_clean_listing_passes(self):
        products, _ = parse_csv_feed(CSV_TEXT)
        issues = {i["type"] for i in analyze_product(products[2], set())}
        assert "title_all_caps" not in issues
        assert "missing_description" not in issues

    def test_missing_required_fields(self):
        products, _ = parse_csv_feed(CSV_TEXT)
        issues = {i["type"] for i in analyze_product(products[3], set())}
        assert {"missing_price", "missing_link", "missing_brand"} <= issues


class TestSkuBudgets:
    def test_unpaid_always_trial(self):
        assert feed_sku_budget_for(None, None) == 10
        assert feed_sku_budget_for("agency", "trialing") == 10
        assert feed_sku_budget_for("agency", "past_due") == 10

    def test_paid_tiers(self):
        assert feed_sku_budget_for("starter", "active") == 100
        assert feed_sku_budget_for("growth", "active") == 1000
        assert feed_sku_budget_for("agency", "active") == 10000


class TestImportAndExport:
    def _store(self):
        store = {"feeds": [], "products": []}

        def db(method, path, payload=None, params=""):
            if method == "post" and path == "product_feeds":
                row = {**payload, "id": 1}
                store["feeds"].append(row)
                return [row]
            if method == "post" and path == "feed_products":
                row = {**payload, "id": len(store["products"]) + 1}
                store["products"].append(row)
                return [row]
            if method == "get" and path == "feed_products":
                rows = store["products"]
                if "optimization_status=eq.optimized" in params:
                    rows = [r for r in rows if r.get("optimization_status") == "optimized"]
                return rows
            return []

        return store, db

    def test_import_analyzes_and_stores(self):
        store, db = self._store()
        result = asyncio.run(
            FeedService().import_feed("proj-1", "Catalog", csv_text=CSV_TEXT, db_fn=db)
        )
        assert result["product_count"] == 4
        assert result["stored"] == 4
        assert result["issue_count"] > 5
        assert result["truncated"] is False
        assert store["feeds"][0]["product_count"] == 4

    def test_import_requires_input(self):
        import pytest
        _, db = self._store()
        with pytest.raises(ValueError):
            asyncio.run(FeedService().import_feed("p", "n", db_fn=db))

    def test_supplemental_export(self):
        store, db = self._store()
        asyncio.run(FeedService().import_feed("proj-1", "Catalog", csv_text=CSV_TEXT, db_fn=db))
        store["products"][0]["optimization_status"] = "optimized"
        store["products"][0]["optimized_title"] = "Acme Blue Running Shoes - Men's Mesh"
        out = FeedService().export_supplemental_feed(1, db)
        lines = out.strip().splitlines()
        assert lines[0] == "id,title,description"
        assert "Acme Blue Running Shoes" in lines[1]

    def test_import_cap_exists(self):
        assert IMPORT_CAP >= 1000
