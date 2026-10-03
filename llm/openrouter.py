import httpx
from llm.base import BaseLLM

class OpenRouterLLM(BaseLLM):
    name = "openrouter"

    def __init__(self, api_key: str, model: str = "openrouter/free"):
        self.api_key = api_key
        self.model = model

    async def generate(self, prompt: str, system: str = "") -> str:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system or "You are a helpful assistant.",
                },
                {"role": "user", "content": prompt},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://opportune-ai.local",
            "X-Title": "Opportune AI",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
