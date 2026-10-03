from config.settings import GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY
from llm.fallback import FallbackLLM
from llm.gemini import GeminiLLM
from llm.groq import GroqLLM
from llm.openrouter import OpenRouterLLM

class LLMManager:
    def __init__(self):
        self.providers = []
        self.last_errors = []

        if GEMINI_API_KEY:
            self.providers.append(GeminiLLM(GEMINI_API_KEY))

        if GROQ_API_KEY:
            self.providers.append(GroqLLM(GROQ_API_KEY))

        if OPENROUTER_API_KEY:
            self.providers.append(OpenRouterLLM(OPENROUTER_API_KEY))

        self.providers.append(FallbackLLM())

    @property
    def has_external_provider(self) -> bool:
        return any(getattr(provider, "name", "fallback") != "fallback" for provider in self.providers)

    async def generate(self, prompt: str, system: str = "") -> str:
        self.last_errors = []
        for provider in self.providers:
            try:
                return await provider.generate(prompt, system)
            except Exception as exc:
                self.last_errors.append({"provider": getattr(provider, "name", "unknown"), "error": str(exc)[:500]})
                continue

        return await FallbackLLM().generate(prompt, system)
