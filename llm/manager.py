import os
from config.settings import GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
from llm.fallback import FallbackLLM
from llm.gemini import GeminiLLM
from llm.groq import GroqLLM
from llm.openrouter import OpenRouterLLM

class LLMManager:
    def __init__(self):
        self.providers=[]
        if GEMINI_API_KEY: self.providers.append(GeminiLLM(GEMINI_API_KEY))
        if GROQ_API_KEY: self.providers.append(GroqLLM(GROQ_API_KEY))
        if OPENROUTER_API_KEY: self.providers.append(OpenRouterLLM(OPENROUTER_API_KEY))
        self.providers.append(FallbackLLM())

    @property
    def has_external_provider(self):
        return any(getattr(p,"name","fallback")!="fallback" for p in self.providers)

    async def generate(self, prompt: str, system: str="") -> str:
        for provider in self.providers:
            try:
                return await provider.generate(prompt, system)
            except Exception:
                continue
        return await FallbackLLM().generate(prompt, system)

    async def generate_external(self, prompt: str, system: str="") -> str:
        """Try each configured external provider in order (Gemini, Groq, OpenRouter); never the canned fallback."""
        errors=[]
        for provider in self.providers:
            name=getattr(provider,"name","fallback")
            if name=="fallback":
                continue
            try:
                text=await provider.generate(prompt, system)
                if str(text or "").strip():
                    return text
                errors.append(f"{name}: empty response")
            except Exception as exc:
                errors.append(f"{name}: {type(exc).__name__}")
        raise RuntimeError("No external LLM provider is available." + (" (" + "; ".join(errors) + ")" if errors else ""))

    async def search_web(self, prompt: str, max_results: int=20) -> list[dict]:
        # 1) Real Google Search grounding through Gemini.
        for provider in self.providers:
            if getattr(provider,"name","")=="gemini" and hasattr(provider,"search_web"):
                try:
                    return await provider.search_web(prompt, max_results=max_results)
                except Exception:
                    pass
        # 2) Direct Serper/Google fallback when configured.
        if SERPER_API_KEY:
            import httpx
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    r=await client.post(
                        "https://google.serper.dev/search",
                        headers={"X-API-KEY":SERPER_API_KEY,"Content-Type":"application/json"},
                        json={"q":prompt,"num":min(max_results,20)},
                    )
                    r.raise_for_status()
                    data=r.json()
                    return [
                        {"title":x.get("title",""),"url":x.get("link",""),"snippet":x.get("snippet","")}
                        for x in data.get("organic",[]) if x.get("link")
                    ]
            except Exception:
                pass
        return []
