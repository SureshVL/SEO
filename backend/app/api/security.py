from fastapi import Header, HTTPException

from app.core.config import settings


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if x_api_key != settings.orchestrator_api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
