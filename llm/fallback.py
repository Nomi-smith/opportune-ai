from llm.base import BaseLLM

class FallbackLLM(BaseLLM):
    name = "fallback"

    async def generate(self, prompt: str, system: str = "") -> str:
        return (
            "No LLM provider is configured or available. "
            "Opportune AI can still use structured discovery, matching, "
            "documents, and application tracking."
        )
