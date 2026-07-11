"""AI generation endpoint — standalone route for direct LLM access."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.security import require_api_key
from app.clients.llm import get_llm_client

router = APIRouter(tags=["AI"])


class GenerateRequest(BaseModel):
    prompt: str
    system: str = ""
    max_tokens: int = 2048
    temperature: float = 0.3


class GenerateResponse(BaseModel):
    result: str
    model: str
    tokens_used: int
    cost_usd: float


@router.post("/generate", response_model=GenerateResponse)
async def generate(
    body: GenerateRequest,
    _auth: str = Depends(require_api_key),
):
    """Generate text using the configured LLM (Claude or Gemini)."""
    client = get_llm_client()
    if not client:
        raise HTTPException(
            status_code=400,
            detail="No LLM configured. Set ANTHROPIC_API_KEY or GEMINI_API_KEY in .env",
        )

    import asyncio
    resp = await asyncio.to_thread(
        client.complete,
        messages=[{"role": "user", "content": body.prompt}],
        system=body.system,
        max_tokens=body.max_tokens,
        temperature=body.temperature,
    )

    return GenerateResponse(
        result=resp.get("content", ""),
        model=resp.get("model", ""),
        tokens_used=resp.get("input_tokens", 0) + resp.get("output_tokens", 0),
        cost_usd=resp.get("cost_usd", 0.0),
    )


@router.post("/generate-json")
async def generate_json(
    body: GenerateRequest,
    _auth: str = Depends(require_api_key),
):
    """Generate structured JSON using the configured LLM."""
    client = get_llm_client()
    if not client:
        raise HTTPException(status_code=400, detail="No LLM configured.")

    import asyncio
    parsed, resp = await asyncio.to_thread(
        client.complete_json,
        messages=[{"role": "user", "content": body.prompt}],
        system=body.system,
        max_tokens=body.max_tokens,
        temperature=body.temperature,
    )

    return {
        "result": parsed,
        "model": resp.get("model", ""),
        "tokens_used": resp.get("input_tokens", 0) + resp.get("output_tokens", 0),
        "cost_usd": resp.get("cost_usd", 0.0),
    }
