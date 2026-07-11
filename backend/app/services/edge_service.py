"""Edge snippet injection - deploy SEO fixes to any website via one <script> tag.

The client adds the snippet to their <head>. On every pageview the snippet
fetches this project's rules for the current URL and applies them in the DOM:
JSON-LD schema, title, meta description, canonical, hreflang, custom metas.
Works on custom-built sites, e-commerce storefronts and legacy platforms
where no CMS API exists.
"""

from __future__ import annotations

import logging
import secrets
import time
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlparse

logger = logging.getLogger("omnirank.edge")

ALLOWED_RULE_TYPES = {"schema", "title", "meta_description", "canonical", "hreflang", "meta"}
ALLOWED_MATCH_TYPES = {"exact", "prefix", "contains", "all"}

# The loader served at GET /edge/v1/omnirank.js — zero dependencies, ~1.5 KB.
EDGE_SNIPPET_JS = r"""(function () {
  var s = document.currentScript;
  if (!s) return;
  var token = s.getAttribute("data-site");
  if (!token) return;
  var api = s.getAttribute("data-api") || new URL(s.src).origin;

  function upsert(sel, tag, attrs) {
    var el = document.head.querySelector(sel);
    if (!el) { el = document.createElement(tag); document.head.appendChild(el); }
    for (var k in attrs) el.setAttribute(k, attrs[k]);
    el.setAttribute("data-omnirank", "1");
  }

  function apply(data) {
    try {
      (data.directives || []).forEach(function (r) {
        var p = r.payload || {};
        if (r.rule_type === "schema" && p.jsonld) {
          var el = document.createElement("script");
          el.type = "application/ld+json";
          el.setAttribute("data-omnirank", "1");
          el.textContent = typeof p.jsonld === "string" ? p.jsonld : JSON.stringify(p.jsonld);
          document.head.appendChild(el);
        } else if (r.rule_type === "title" && p.value) {
          document.title = p.value;
        } else if (r.rule_type === "meta_description" && p.value) {
          upsert('meta[name="description"]', "meta", { name: "description", content: p.value });
        } else if (r.rule_type === "canonical" && p.href) {
          upsert('link[rel="canonical"]', "link", { rel: "canonical", href: p.href });
        } else if (r.rule_type === "hreflang" && p.links) {
          p.links.forEach(function (l) {
            if (!l.hreflang || !l.href) return;
            var e = document.createElement("link");
            e.rel = "alternate"; e.hreflang = l.hreflang; e.href = l.href;
            e.setAttribute("data-omnirank", "1");
            document.head.appendChild(e);
          });
        } else if (r.rule_type === "meta" && p.name && p.content) {
          upsert('meta[name="' + p.name + '"]', "meta", { name: p.name, content: p.content });
        }
      });
    } catch (e) { /* never break the host page */ }
  }

  function load() {
    fetch(api + "/edge/v1/config?token=" + encodeURIComponent(token) +
          "&url=" + encodeURIComponent(location.pathname))
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { if (d) apply(d); })
      .catch(function () {});
  }

  window.OmniRank = { refresh: load };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", load);
  } else {
    load();
  }
})();
"""


def _norm_path(url_or_path: str) -> str:
    """Normalize a URL or path to a comparable path string."""
    raw = (url_or_path or "").strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        raw = urlparse(raw).path or "/"
    if "?" in raw:
        raw = raw.split("?", 1)[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    if len(raw) > 1 and raw.endswith("/"):
        raw = raw.rstrip("/")
    return raw or "/"


def rule_matches(rule: dict[str, Any], path: str) -> bool:
    """Does a rule apply to this normalized path?"""
    pattern = rule.get("url_pattern", "") or "*"
    match_type = rule.get("match_type", "exact")
    if pattern == "*" or match_type == "all":
        return True
    norm_pattern = _norm_path(pattern)
    if match_type == "exact":
        return path == norm_pattern
    if match_type == "prefix":
        return path.startswith(norm_pattern)
    if match_type == "contains":
        return norm_pattern.strip("/") in path
    return False


class EdgeService:
    """Manages edge sites, rules, and directive resolution for the snippet."""

    # (token) -> (expires_at_epoch, site_row, rules)
    _cache: dict[str, tuple[float, dict, list[dict]]] = {}
    _cache_ttl = 60.0
    # token -> last time we persisted last_seen_at (throttle writes)
    _seen_writes: dict[str, float] = {}

    # ── Sites ───────────────────────────────────────────────────────

    def create_site(self, project_id: str, domain: str, db_fn: Callable) -> dict[str, Any]:
        domain = domain.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
        token = "or_" + secrets.token_urlsafe(24)
        rows = db_fn("post", "edge_sites", {
            "project_id": project_id,
            "domain": domain,
            "site_token": token,
            "enabled": True,
        })
        row = rows[0] if isinstance(rows, list) and rows else rows
        logger.info("Created edge site %s for %s", domain, project_id)
        return row

    def get_sites(self, project_id: str, db_fn: Callable) -> list[dict[str, Any]]:
        rows = db_fn("get", "edge_sites", params=f"project_id=eq.{project_id}&order=created_at.desc")
        return rows if isinstance(rows, list) else [rows] if rows else []

    async def verify_site(self, site: dict[str, Any], db_fn: Callable) -> dict[str, Any]:
        """Fetch the site's homepage and check the snippet is installed."""
        import httpx

        domain = site["domain"]
        token = site["site_token"]
        found = False
        error = ""
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(f"https://{domain}")
                html = resp.text[:800_000]
                found = ("omnirank.js" in html) and (token in html)
        except Exception as exc:
            error = str(exc)[:200]

        if found:
            db_fn("patch", f"edge_sites?id=eq.{site['id']}", {
                "verified": True,
                "verified_at": datetime.now(timezone.utc).isoformat(),
            })
        return {"verified": found, "error": error or None}

    # ── Rules ───────────────────────────────────────────────────────

    def create_rule(
        self,
        project_id: str,
        site_id: str,
        url_pattern: str,
        match_type: str,
        rule_type: str,
        payload: dict[str, Any],
        source: str = "manual",
        notes: str = "",
        db_fn: Callable | None = None,
    ) -> dict[str, Any]:
        if rule_type not in ALLOWED_RULE_TYPES:
            raise ValueError(f"rule_type must be one of {sorted(ALLOWED_RULE_TYPES)}")
        if match_type not in ALLOWED_MATCH_TYPES:
            raise ValueError(f"match_type must be one of {sorted(ALLOWED_MATCH_TYPES)}")
        import json as _json
        rows = db_fn("post", "edge_rules", {
            "project_id": project_id,
            "site_id": site_id,
            "url_pattern": url_pattern or "*",
            "match_type": match_type,
            "rule_type": rule_type,
            "payload": _json.dumps(payload) if not isinstance(payload, str) else payload,
            "enabled": True,
            "source": source,
            "notes": notes,
        })
        self._invalidate_cache()
        return rows[0] if isinstance(rows, list) and rows else rows

    def get_rules(
        self,
        project_id: str,
        site_id: str | None = None,
        db_fn: Callable | None = None,
    ) -> list[dict[str, Any]]:
        params = f"project_id=eq.{project_id}&order=created_at.desc"
        if site_id:
            params += f"&site_id=eq.{site_id}"
        rows = db_fn("get", "edge_rules", params=params)
        return rows if isinstance(rows, list) else [rows] if rows else []

    def update_rule(self, rule_id: int, changes: dict[str, Any], db_fn: Callable) -> bool:
        allowed = {"enabled", "url_pattern", "match_type", "payload", "priority", "notes"}
        patch = {k: v for k, v in changes.items() if k in allowed}
        if not patch:
            return False
        if "payload" in patch and not isinstance(patch["payload"], str):
            import json as _json
            patch["payload"] = _json.dumps(patch["payload"])
        patch["updated_at"] = datetime.now(timezone.utc).isoformat()
        db_fn("patch", f"edge_rules?id=eq.{rule_id}", patch)
        self._invalidate_cache()
        return True

    def delete_rule(self, rule_id: int, db_fn: Callable) -> bool:
        db_fn("delete", f"edge_rules?id=eq.{rule_id}")
        self._invalidate_cache()
        return True

    # ── Directive resolution (hot path: called on every pageview) ───

    def resolve_directives(self, token: str, url: str, db_fn: Callable) -> dict[str, Any] | None:
        """Rules that apply to this URL, for the public config endpoint.

        Returns None for unknown/disabled tokens. Cached for 60s per site.
        """
        entry = self._cache.get(token)
        now = time.time()
        if entry and entry[0] > now:
            site, rules = entry[1], entry[2]
        else:
            sites = db_fn("get", "edge_sites", params=f"site_token=eq.{token}")
            sites = sites if isinstance(sites, list) else [sites] if sites else []
            if not sites or not sites[0].get("enabled"):
                self._cache[token] = (now + self._cache_ttl, {}, [])
                return None
            site = sites[0]
            rules = db_fn(
                "get", "edge_rules",
                params=f"site_id=eq.{site['id']}&enabled=eq.true&order=priority.desc",
            )
            rules = rules if isinstance(rules, list) else [rules] if rules else []
            self._cache[token] = (now + self._cache_ttl, site, rules)

        if not site:
            return None

        # Throttled heartbeat so the dashboard shows "snippet active"
        if now - self._seen_writes.get(token, 0) > 300:
            self._seen_writes[token] = now
            try:
                db_fn("patch", f"edge_sites?id=eq.{site['id']}", {
                    "last_seen_at": datetime.now(timezone.utc).isoformat(),
                })
            except Exception:
                pass

        path = _norm_path(url)
        import json as _json
        directives = []
        for rule in rules:
            if not rule_matches(rule, path):
                continue
            payload = rule.get("payload")
            if isinstance(payload, str):
                try:
                    payload = _json.loads(payload)
                except (ValueError, TypeError):
                    continue
            directives.append({"rule_type": rule["rule_type"], "payload": payload})

        return {"directives": directives}

    @classmethod
    def _invalidate_cache(cls) -> None:
        cls._cache.clear()
