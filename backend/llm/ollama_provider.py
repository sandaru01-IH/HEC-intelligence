import json
from typing import AsyncGenerator, Optional

import httpx

from backend.config import LLM_MODEL, OLLAMA_BASE_URL, SYSTEM_PROMPT
from backend.llm.base import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    def __init__(self, model: str = LLM_MODEL, base_url: str = OLLAMA_BASE_URL):
        self._model = model
        self._base_url = base_url.rstrip("/")

    def model_name(self) -> str:
        return self._model

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{self._base_url}/api/tags")
                if r.status_code != 200:
                    return False
                models = [m["name"] for m in r.json().get("models", [])]
                return any(self._model in m for m in models)
        except Exception:
            return False

    async def stream(
        self,
        user_query: str,
        context: str,
        system_prompt: str = SYSTEM_PROMPT,
        model_override: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        active_model = model_override or self._model
        prompt = self._build_prompt(user_query, context)
        payload = {
            "model": active_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/api/chat",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if data.get("done", False):
                        break

    @staticmethod
    def _build_prompt(user_query: str, context: str) -> str:
        if not context.strip():
            return (
                f"Question: {user_query}\n\n"
                "Note: No specific records were retrieved for this query. "
                "Answer based on your domain knowledge, and clearly indicate limited source availability."
            )
        return (
            f"RETRIEVED CONTEXT:\n{context}\n\n"
            f"USER QUESTION: {user_query}"
        )
