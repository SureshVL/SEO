import json

from fastapi import Header, HTTPException

from app.core.config import settings


def _key_map() -> dict:
    try:
        data = json.loads(settings.orchestrator_keys_json or "{}")
        if isinstance(data, dict):
            return data
    except Exception:  # noqa: BLE001
        pass
    return {}


def require_api_key(x_api_key: str | None = Header(default=None)) -> str:
    keys = _key_map()
    if keys:
        if not x_api_key or x_api_key not in keys:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return x_api_key

    if x_api_key != settings.orchestrator_api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return x_api_key or ""


def require_project_access(project_id: str, api_key: str) -> None:
    keys = _key_map()
    if not keys:
        return
    scopes = keys.get(api_key, {})
    allowed = scopes.get("projects", ["*"])
    if "*" not in allowed and project_id not in allowed:
        raise HTTPException(status_code=403, detail="Forbidden for project")
