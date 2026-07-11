"""Git-based write-back: open pull requests with SEO fixes on client repos.

For headless/JAMstack/static-site clients, fixes ship as reviewable pull
requests instead of CMS pushes: new content files, schema components,
meta/config changes, redirect maps.
"""

from __future__ import annotations

import base64
import json
import logging
import secrets
from datetime import datetime, timezone
from typing import Any, Callable

import httpx

logger = logging.getLogger("omnirank.git")

GITHUB_API = "https://api.github.com"
FIX_TYPES = {"content", "schema", "meta", "redirects", "hreflang", "other"}


class GitHubClient:
    """Minimal GitHub REST client (contents + refs + pulls). No SDK."""

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "OmniRank/1.0",
        }

    def _client(self) -> httpx.Client:
        return httpx.Client(headers=self.headers, timeout=30)

    def get_repo(self, owner: str, repo: str) -> dict[str, Any]:
        with self._client() as c:
            r = c.get(f"{GITHUB_API}/repos/{owner}/{repo}")
            r.raise_for_status()
            return r.json()

    def get_branch_sha(self, owner: str, repo: str, branch: str) -> str:
        with self._client() as c:
            r = c.get(f"{GITHUB_API}/repos/{owner}/{repo}/git/ref/heads/{branch}")
            r.raise_for_status()
            return r.json()["object"]["sha"]

    def create_branch(self, owner: str, repo: str, branch: str, from_sha: str) -> None:
        with self._client() as c:
            r = c.post(
                f"{GITHUB_API}/repos/{owner}/{repo}/git/refs",
                json={"ref": f"refs/heads/{branch}", "sha": from_sha},
            )
            r.raise_for_status()

    def get_file_sha(self, owner: str, repo: str, path: str, ref: str) -> str | None:
        with self._client() as c:
            r = c.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}",
                params={"ref": ref},
            )
            if r.status_code == 404:
                return None
            r.raise_for_status()
            data = r.json()
            return data.get("sha") if isinstance(data, dict) else None

    def put_file(
        self, owner: str, repo: str, path: str, content: str,
        message: str, branch: str, sha: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "message": message,
            "content": base64.b64encode(content.encode()).decode(),
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha
        with self._client() as c:
            r = c.put(f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}", json=payload)
            r.raise_for_status()

    def create_pull_request(
        self, owner: str, repo: str, title: str, body: str, head: str, base: str,
    ) -> dict[str, Any]:
        with self._client() as c:
            r = c.post(
                f"{GITHUB_API}/repos/{owner}/{repo}/pulls",
                json={"title": title, "body": body, "head": head, "base": base},
            )
            r.raise_for_status()
            return r.json()

    def get_pull_request(self, owner: str, repo: str, number: int) -> dict[str, Any]:
        with self._client() as c:
            r = c.get(f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{number}")
            r.raise_for_status()
            return r.json()


def _strip_token(row: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in row.items() if k != "access_token"}


class GitWritebackService:
    """Connect repos and ship SEO fixes as pull requests."""

    def connect_repo(
        self,
        project_id: str,
        repo_owner: str,
        repo_name: str,
        base_branch: str,
        access_token: str,
        db_fn: Callable,
    ) -> dict[str, Any]:
        """Verify access with the token, then store the connection."""
        gh = GitHubClient(access_token)
        try:
            repo = gh.get_repo(repo_owner, repo_name)
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            if code in (401, 403):
                raise ValueError("Token rejected by GitHub. Use a fine-grained PAT with Contents + Pull requests read/write.")
            if code == 404:
                raise ValueError("Repository not found (check owner/name, and that the token can see it).")
            raise

        base = base_branch or repo.get("default_branch", "main")
        rows = db_fn("post", "git_connections", {
            "project_id": project_id,
            "provider": "github",
            "repo_owner": repo_owner,
            "repo_name": repo_name,
            "base_branch": base,
            "access_token": access_token,
            "enabled": True,
            "verified": True,
            "verified_at": datetime.now(timezone.utc).isoformat(),
        })
        row = rows[0] if isinstance(rows, list) and rows else rows
        logger.info("Connected repo %s/%s for project %s", repo_owner, repo_name, project_id)
        return _strip_token(row if isinstance(row, dict) else {})

    def get_connections(self, project_id: str, db_fn: Callable) -> list[dict[str, Any]]:
        rows = db_fn("get", "git_connections", params=f"project_id=eq.{project_id}&order=created_at.desc")
        rows = rows if isinstance(rows, list) else [rows] if rows else []
        return [_strip_token(r) for r in rows]

    def delete_connection(self, connection_id: str, db_fn: Callable) -> bool:
        db_fn("delete", f"git_connections?id=eq.{connection_id}")
        return True

    def open_fix_pr(
        self,
        project_id: str,
        connection_id: str,
        title: str,
        description: str,
        fix_type: str,
        files: list[dict[str, str]],
        db_fn: Callable,
    ) -> dict[str, Any]:
        """Create a branch, commit the fix files, and open a pull request."""
        if fix_type not in FIX_TYPES:
            raise ValueError(f"fix_type must be one of {sorted(FIX_TYPES)}")
        if not files:
            raise ValueError("At least one file is required")
        for f in files:
            if not f.get("path") or f.get("content") is None:
                raise ValueError("Each file needs a path and content")

        rows = db_fn("get", "git_connections", params=f"id=eq.{connection_id}")
        rows = rows if isinstance(rows, list) else [rows] if rows else []
        if not rows:
            raise ValueError("Git connection not found")
        conn = rows[0]
        if not conn.get("enabled"):
            raise ValueError("Git connection is disabled")

        owner, repo, base = conn["repo_owner"], conn["repo_name"], conn["base_branch"]
        gh = GitHubClient(conn["access_token"])

        branch = f"omnirank/{fix_type}-{secrets.token_hex(4)}"
        base_sha = gh.get_branch_sha(owner, repo, base)
        gh.create_branch(owner, repo, branch, base_sha)

        committed = []
        for f in files:
            path = f["path"].lstrip("/")
            existing_sha = gh.get_file_sha(owner, repo, path, base)
            gh.put_file(
                owner, repo, path, f["content"],
                message=f"seo: {title} ({path})",
                branch=branch,
                sha=existing_sha,
            )
            committed.append({"path": path, "action": "update" if existing_sha else "create"})

        body = (
            f"{description.strip()}\n\n---\n"
            f"**Fix type:** {fix_type}\n"
            f"**Files:** " + ", ".join(c["path"] for c in committed) + "\n\n"
            "Opened automatically by [OMNI-RANK](https://omnirank.ai) — review and merge to ship this SEO fix."
        )
        pr = gh.create_pull_request(owner, repo, title, body, head=branch, base=base)

        record = {
            "project_id": project_id,
            "connection_id": connection_id,
            "pr_number": pr.get("number"),
            "pr_url": pr.get("html_url"),
            "branch_name": branch,
            "title": title,
            "description": description,
            "fix_type": fix_type,
            "files": json.dumps(committed),
            "status": "open",
        }
        try:
            db_fn("post", "git_pull_requests", record)
        except Exception as exc:
            logger.warning("Could not store PR record: %s", exc)

        logger.info("Opened PR #%s on %s/%s: %s", pr.get("number"), owner, repo, title)
        return {
            "pr_number": pr.get("number"),
            "pr_url": pr.get("html_url"),
            "branch": branch,
            "files": committed,
        }

    def list_prs(self, project_id: str, db_fn: Callable, sync: bool = True) -> list[dict[str, Any]]:
        rows = db_fn("get", "git_pull_requests", params=f"project_id=eq.{project_id}&order=created_at.desc")
        rows = rows if isinstance(rows, list) else [rows] if rows else []

        if sync:
            # refresh status of the newest open PRs, best-effort
            open_prs = [r for r in rows if r.get("status") == "open"][:10]
            conns: dict[str, dict] = {}
            for pr in open_prs:
                cid = pr.get("connection_id")
                if cid not in conns:
                    crows = db_fn("get", "git_connections", params=f"id=eq.{cid}")
                    crows = crows if isinstance(crows, list) else [crows] if crows else []
                    conns[cid] = crows[0] if crows else {}
                conn = conns.get(cid) or {}
                if not conn.get("access_token") or not pr.get("pr_number"):
                    continue
                try:
                    gh = GitHubClient(conn["access_token"])
                    remote = gh.get_pull_request(conn["repo_owner"], conn["repo_name"], pr["pr_number"])
                    new_status = "merged" if remote.get("merged_at") else remote.get("state", "open")
                    if new_status != pr.get("status"):
                        db_fn("patch", f"git_pull_requests?id=eq.{pr['id']}", {"status": new_status})
                        pr["status"] = new_status
                except Exception:
                    continue

        return rows
