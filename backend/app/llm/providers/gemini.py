import json
from typing import Any

from google import genai

from app.config.settings import GEMINI_API_KEY, GEMINI_MODEL
from app.llm.gateway import LLMProvider


class GeminiProvider(LLMProvider):
    """Gemini implementation of the provider-neutral LLM interface."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
    ):
        resolved_api_key = api_key or GEMINI_API_KEY

        if not resolved_api_key:
            raise ValueError("GEMINI_API_KEY is required for GeminiProvider.")

        self._client = genai.Client(api_key=resolved_api_key)
        self._model = model or GEMINI_MODEL

    def generate(
        self,
        *,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        contents = prompt

        if context:
            contents = (
                f"{prompt}\n\n"
                "Structured PaymentOps context:\n"
                f"{json.dumps(context, default=str, sort_keys=True)}"
            )

        response = self._client.models.generate_content(
            model=self._model,
            contents=contents,
        )

        text = getattr(response, "text", None)

        if not text:
            raise RuntimeError("Gemini returned an empty response.")

        return text.strip()
