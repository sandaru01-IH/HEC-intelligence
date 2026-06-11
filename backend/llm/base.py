from abc import ABC, abstractmethod
from typing import AsyncGenerator


class BaseLLMProvider(ABC):
    """Swap any provider (Ollama, HuggingFace, OpenAI-compat) by implementing this interface."""

    @abstractmethod
    async def stream(
        self,
        user_query: str,
        context: str,
        system_prompt: str,
    ) -> AsyncGenerator[str, None]:
        """Yield response tokens as they are generated."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the LLM backend is reachable and the model is loaded."""
        ...

    @abstractmethod
    def model_name(self) -> str:
        """Return the active model identifier string."""
        ...
