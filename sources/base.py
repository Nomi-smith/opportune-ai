from abc import ABC, abstractmethod
from models.opportunity import Opportunity

class BaseSource(ABC):
    name: str = "Unknown Source"

    @abstractmethod
    async def search(
        self,
        query: str,
        opportunity_type: str | None = None,
        country: str | None = None,
    ) -> list[Opportunity]:
        raise NotImplementedError
