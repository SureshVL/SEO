import os
from groq import Groq
from typing import List, Dict, Any
from app.core.config import settings

class GroqClient:
    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key or os.getenv("GROQ_API_KEY"))

    def complete(self, messages: List[Dict], model: str = "llama-3.3-70b-versatile",
                 temperature: float = 0.7, max_tokens: int = 4000, **kwargs) -> Dict:
        response = self.client.chat.completions.create(
            model=model, messages=messages,
            temperature=temperature, max_tokens=max_tokens, **kwargs
        )
        return {
            "content": response.choices[0].message.content,
            "model": model, "provider": "groq",
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "cost_usd": 0.0
        }
