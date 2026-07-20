"""Social media content generation, calendar, and approval workflow.

Phase 1 of the social module: AI caption/hashtag generation per platform,
a social content calendar backed by Supabase, and a client approval flow
with a capped number of revision rounds (agency contract: 2 rounds).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, Optional

logger = logging.getLogger("omnirank.social")

MAX_REVISION_ROUNDS = 2

SUPPORTED_PLATFORMS = ["instagram", "facebook", "tiktok", "youtube", "linkedin"]

# Platform constraints fed to the LLM so output is native to each network.
PLATFORM_SPECS: dict[str, dict[str, Any]] = {
    "instagram": {
        "caption_max_chars": 2200,
        "ideal_caption_chars": 150,
        "hashtags": "8-15 niche + branded hashtags",
        "style": "visual-first, hook in the first line (it gets truncated), emoji-friendly, CTA to save/share/comment",
    },
    "facebook": {
        "caption_max_chars": 63206,
        "ideal_caption_chars": 80,
        "hashtags": "0-3 hashtags max (hashtags underperform on Facebook)",
        "style": "conversational, question-led to drive comments, link-friendly",
    },
    "tiktok": {
        "caption_max_chars": 2200,
        "ideal_caption_chars": 100,
        "hashtags": "3-6 hashtags mixing trending + niche",
        "style": "casual, trend-aware, hook framed for video overlay text",
    },
    "youtube": {
        "caption_max_chars": 5000,
        "ideal_caption_chars": 300,
        "hashtags": "3-5 hashtags",
        "style": "keyword-rich first 2 lines (search matters), timestamps placeholder, subscribe CTA",
    },
    "linkedin": {
        "caption_max_chars": 3000,
        "ideal_caption_chars": 200,
        "hashtags": "3-5 professional hashtags",
        "style": "professional but human, insight-led, line breaks for skimmability, no emoji overload",
    },
}

VALID_STATUSES = [
    "draft",              # generated / being edited internally
    "pending_approval",   # sent to client
    "revision_requested", # client asked for changes (counts a round)
    "approved",           # client signed off
    "scheduled",          # approved + has a publish date
    "published",          # manually marked published (Phase 1 has no auto-posting)
]

CONTENT_GOALS = ["educational", "promotional", "engagement", "brand_awareness"]


def generate_social_posts(
    llm_client,
    topic: str,
    platforms: list[str],
    tone: str = "friendly",
    business_context: str = "",
    content_goal: str = "engagement",
) -> dict[str, Any]:
    """Generate platform-native captions + hashtags for one topic."""
    platforms = [p.lower() for p in platforms if p.lower() in SUPPORTED_PLATFORMS]
    if not platforms:
        raise ValueError(f"No valid platforms. Supported: {SUPPORTED_PLATFORMS}")
    if content_goal not in CONTENT_GOALS:
        content_goal = "engagement"

    spec_lines = "\n".join(
        f"- {p}: ideal length ~{PLATFORM_SPECS[p]['ideal_caption_chars']} chars, "
        f"hashtags: {PLATFORM_SPECS[p]['hashtags']}, style: {PLATFORM_SPECS[p]['style']}"
        for p in platforms
    )

    prompt = f"""You are a senior social media copywriter. Write platform-native content.

TOPIC: {topic}
BUSINESS CONTEXT: {business_context or "not provided"}
TONE: {tone}
CONTENT GOAL: {content_goal}

PLATFORM RULES:
{spec_lines}

Return ONLY valid JSON in exactly this shape (keys = platform names):
{{
  "<platform>": {{
    "hook": "first line / opening hook",
    "caption": "full caption ready to paste (without hashtags)",
    "hashtags": ["#tag1", "#tag2"],
    "cta": "the call to action used",
    "best_time_hint": "e.g. Tue/Thu 11am-1pm local"
  }}
}}
Write real, specific copy for the topic — no placeholders like [Product]."""

    parsed, raw = llm_client.complete_json(
        [{"role": "user", "content": prompt}], temperature=0.8, max_tokens=2500
    )

    results: dict[str, Any] = {}
    for p in platforms:
        block = parsed.get(p) if isinstance(parsed, dict) else None
        if isinstance(block, dict) and block.get("caption"):
            block.setdefault("hashtags", [])
            block.setdefault("hook", "")
            block.setdefault("cta", "")
            block.setdefault("best_time_hint", "")
            results[p] = block
        else:
            results[p] = {"error": "generation failed for this platform"}

    return {
        "topic": topic,
        "tone": tone,
        "content_goal": content_goal,
        "platforms": results,
        "model_used": raw.get("_provider_used") if isinstance(raw, dict) else None,
    }


class SocialPostManager:
    """CRUD + approval workflow for social calendar posts (Supabase REST)."""

    def __init__(self, db_fn: Callable):
        # db_fn is main._supabase_rest(method, path, payload=None, params="")
        self.db = db_fn

    def create_post(self, project_id: str, payload: dict) -> dict:
        platform = str(payload.get("platform", "")).lower()
        if platform not in SUPPORTED_PLATFORMS:
            raise ValueError(f"Invalid platform '{platform}'. Supported: {SUPPORTED_PLATFORMS}")
        row = {
            "project_id": project_id,
            "platform": platform,
            "topic": payload.get("topic", ""),
            "caption": payload.get("caption", ""),
            "hashtags": payload.get("hashtags", []),
            "content_goal": payload.get("content_goal", "engagement"),
            "media_notes": payload.get("media_notes", ""),
            "scheduled_date": payload.get("scheduled_date"),
            "status": "draft",
            "revision_count": 0,
            "revision_notes": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        data = self.db("post", "social_posts", row)
        return data[0] if isinstance(data, list) else data

    def list_posts(
        self, project_id: str, status: Optional[str] = None, platform: Optional[str] = None
    ) -> list:
        params = f"project_id=eq.{project_id}&order=scheduled_date.asc.nullslast,created_at.desc"
        if status:
            params += f"&status=eq.{status}"
        if platform:
            params += f"&platform=eq.{platform.lower()}"
        return self.db("get", "social_posts", params=params) or []

    def get_post(self, post_id: str) -> Optional[dict]:
        rows = self.db("get", "social_posts", params=f"id=eq.{post_id}")
        return rows[0] if rows else None

    def update_post(self, post_id: str, updates: dict) -> dict:
        allowed = {
            "caption", "hashtags", "topic", "content_goal", "media_notes",
            "scheduled_date", "status", "platform",
        }
        clean = {k: v for k, v in updates.items() if k in allowed}
        if "status" in clean and clean["status"] not in VALID_STATUSES:
            raise ValueError(f"Invalid status. Valid: {VALID_STATUSES}")
        if "platform" in clean:
            clean["platform"] = str(clean["platform"]).lower()
            if clean["platform"] not in SUPPORTED_PLATFORMS:
                raise ValueError(f"Invalid platform. Supported: {SUPPORTED_PLATFORMS}")
        clean["updated_at"] = datetime.utcnow().isoformat()
        data = self.db("patch", f"social_posts?id=eq.{post_id}", clean)
        return data[0] if isinstance(data, list) and data else clean

    def approve(self, post_id: str) -> dict:
        return self.update_post(post_id, {"status": "approved"})

    def request_revision(self, post_id: str, note: str) -> dict:
        """Client requests changes. Enforces the contract cap of rounds."""
        post = self.get_post(post_id)
        if not post:
            raise LookupError("Post not found")
        count = int(post.get("revision_count") or 0)
        if count >= MAX_REVISION_ROUNDS:
            raise PermissionError(
                f"Revision limit reached ({MAX_REVISION_ROUNDS} rounds included). "
                "Further changes need account manager approval."
            )
        notes = post.get("revision_notes") or []
        notes.append({"round": count + 1, "note": note, "at": datetime.utcnow().isoformat()})
        data = self.db("patch", f"social_posts?id=eq.{post_id}", {
            "status": "revision_requested",
            "revision_count": count + 1,
            "revision_notes": notes,
            "updated_at": datetime.utcnow().isoformat(),
        })
        return data[0] if isinstance(data, list) and data else {"revision_count": count + 1}

    def delete_post(self, post_id: str) -> bool:
        self.db("delete", f"social_posts?id=eq.{post_id}", None)
        return True
