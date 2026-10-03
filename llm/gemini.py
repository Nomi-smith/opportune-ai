import httpx
from llm.base import BaseLLM

class GeminiLLM(BaseLLM):
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-3.8-flash"):
        self.api_key = api_key
        self.model = model

    async def generate(self, prompt: str, system: str = "") -> str:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )
        payload = {
            "contents": [
                {"parts": [{"text": f"{system}\n\n{prompt}"}]}
            ]
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url, params={"key": self.api_key}, json=payload
            )
            response.raise_for_status()
            data = response.json()

        return data["candidates"][0]["content"]["parts"][0]["text"]
