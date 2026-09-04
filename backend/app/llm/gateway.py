from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Provider-neutral interface for LLM text generation."""

    @abstractmethod
    def generate(
        self,
        *,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        raise NotImplementedError


class LLMGateway:
    """Provider-neutral gateway used by PaymentOps AI."""

    def __init__(self, provider: LLMProvider):
        self._provider = provider

    def generate(
        self,
        *,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        return self._provider.generate(
            prompt=prompt,
            context=context,
        )
