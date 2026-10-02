from llm.base import BaseLLM
from llm.fallback import FallbackLLM


class LLMManager:

    def __init__(self):
        self.providers: list[BaseLLM] = []
        self.fallback = FallbackLLM()

    def add_provider(self, provider: BaseLLM):
        self.providers.append(provider)

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
    ) -> str:

        for provider in self.providers:
            try:
                response = provider.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                )

                if response:
                    return response

            except Exception:
                continue

        return self.fallback.generate(
            prompt=prompt,
            system_prompt=system_prompt,
        )