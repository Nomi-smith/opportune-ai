from llm.base import BaseLLM


class FallbackLLM(BaseLLM):

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
    ) -> str:

        return (
            "LLM provider is currently unavailable. "
            "Opportune AI is operating in fallback mode."
        )