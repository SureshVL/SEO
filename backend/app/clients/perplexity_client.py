# backend/app/clients/perplexity_client.py
from openai import OpenAI
from typing import List, Dict, Any
import os

class PerplexityClient:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("PERPLEXITY_API_KEY"),
            base_url="https://api.perplexity.ai"
        )

    def complete(self, messages: List[Dict], model: str = "sonar-pro", 
                 temperature: float = 0.7, max_tokens: int = 4000, **kwargs) -> Dict:
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        return {
            "content": response.choices[0].message.content,
            "model": model,
            "provider": "perplexity",
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "cost_usd": 0.0
        }