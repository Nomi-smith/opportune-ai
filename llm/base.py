from abc import ABC, abstractmethod

class BaseLLM(ABC):
    name = "unknown"

    @abstractmethod
    async def generate(self, prompt: str, system: str = "") -> str:
        raise NotImplementedError
