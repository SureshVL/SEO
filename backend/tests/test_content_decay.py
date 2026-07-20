"""Tests for the content decay analyzer (GSC-driven refresh loop)."""

from app.services.content_decay import DecayItem, analyze_decay, serialize_decay_item


def _row(page, clicks, impressions, position):
    return {"page": page, "clicks": clicks, "impressions": impressions, "position": position}


class TestAnalyzeDecay:
    def test_clicks_drop_flags_page(self):
        now = [_row("/a", 10, 500, 8.0)]
        prev = [_row("/a", 40, 520, 7.5)]
        items = analyze_decay(now, prev)
        assert len(items) == 1
        assert items[0].severity == "critical"  # 75% click drop
        assert any("clicks down" in r for r in items[0].reasons)
        assert items[0].clicks_lost == 30

    def test_position_slide_flags_page(self):
        now = [_row("/b", 20, 600, 14.0)]
        prev = [_row("/b", 22, 610, 6.0)]
        items = analyze_decay(now, prev)
        assert len(items) == 1
        assert any("position slid" in r for r in items[0].reasons)
        assert items[0].severity == "warning"

    def test_low_signal_pages_ignored(self):
        # Only 12 impressions before — noise, not decay
        now = [_row("/c", 0, 2, 30.0)]
        prev = [_row("/c", 3, 12, 25.0)]
        assert analyze_decay(now, prev) == []

    def test_healthy_page_not_flagged(self):
        now = [_row("/d", 50, 1000, 5.0)]
        prev = [_row("/d", 45, 950, 5.5)]
        assert analyze_decay(now, prev) == []

    def test_new_page_without_history_ignored(self):
        now = [_row("/new", 5, 100, 12.0)]
        assert analyze_decay(now, []) == []

    def test_ordering_critical_first_then_clicks_lost(self):
        now = [
            _row("/warn", 30, 400, 12.0),   # position slide only
            _row("/crit", 5, 500, 9.0),     # massive click drop
        ]
        prev = [
            _row("/warn", 32, 420, 8.0),
            _row("/crit", 60, 520, 8.5),
        ]
        items = analyze_decay(now, prev)
        assert [i.page for i in items] == ["/crit", "/warn"]

    def test_top_queries_attached(self):
        now = [_row("/a", 10, 500, 8.0)]
        prev = [_row("/a", 40, 520, 7.5)]
        pq = [
            {"page": "/a", "query": "big query", "impressions": 300, "clicks": 6, "position": 9.0},
            {"page": "/a", "query": "small query", "impressions": 50, "clicks": 1, "position": 15.0},
            {"page": "/other", "query": "irrelevant", "impressions": 900, "clicks": 9, "position": 3.0},
        ]
        items = analyze_decay(now, prev, pq)
        qs = items[0].top_queries
        assert qs[0]["query"] == "big query"
        assert all(q["query"] != "irrelevant" for q in qs)

    def test_serialization_shape(self):
        now = [_row("/a", 10, 500, 8.0)]
        prev = [_row("/a", 40, 520, 7.5)]
        d = serialize_decay_item(analyze_decay(now, prev)[0])
        for key in ("page", "clicks_lost", "reasons", "severity", "top_queries"):
            assert key in d
