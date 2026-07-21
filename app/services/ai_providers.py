from __future__ import annotations

import json
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

import httpx

from app.core.exceptions import AppException


@dataclass(frozen=True)
class AIProviderResult:
    content_by_type: dict[str, str]
    model: str
    cost_usd: Decimal
    latency_ms: int


class AIProvider(Protocol):
    provider_name: str

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        content_types: list[str],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AIProviderResult: ...


class _BaseHTTPProvider:
    provider_name: str

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._timeout = timeout_seconds

    def _json_instruction(self, content_types: list[str]) -> str:
        keys = ", ".join(content_types)
        return (
            "Return valid JSON only. Use these exact keys: "
            f"{keys}. Each value must be a non-empty string."
        )

    def _strip_markdown_code_fences(self, text: str) -> str:
        cleaned = text.strip()
        if not cleaned.startswith("```"):
            return cleaned

        first_newline = cleaned.find("\n")
        if first_newline == -1:
            return cleaned

        opening_fence = cleaned[:first_newline].strip()
        if not opening_fence.startswith("```"):
            return cleaned

        body_and_tail = cleaned[first_newline + 1 :]
        closing_index = body_and_tail.rfind("```")
        if closing_index == -1:
            return cleaned

        body = body_and_tail[:closing_index]
        tail = body_and_tail[closing_index + 3 :].strip()
        if tail:
            return cleaned

        return body.strip()

    def _parse_json(self, text: str, expected_keys: list[str]) -> dict[str, str]:
        try:
            payload = json.loads(self._strip_markdown_code_fences(text))
        except json.JSONDecodeError as exc:
            raise AppException(
                status_code=502, detail="AI provider returned invalid JSON"
            ) from exc

        if not isinstance(payload, dict):
            raise AppException(
                status_code=502, detail="AI provider returned invalid payload"
            )

        out: dict[str, str] = {}
        for key in expected_keys:
            value = payload.get(key)
            if not isinstance(value, str) or not value.strip():
                raise AppException(
                    status_code=502, detail=f"AI provider missing content for {key}"
                )
            out[key] = value.strip()
        return out


class OpenAIProvider(_BaseHTTPProvider):
    provider_name = "openai"

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        content_types: list[str],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AIProviderResult:
        endpoint = (self._base_url or "https://api.openai.com") + "/v1/chat/completions"
        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                endpoint,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": f"{user_prompt}\n\n{self._json_instruction(content_types)}",
                        },
                    ],
                },
            )
        latency_ms = int((time.perf_counter() - start) * 1000)
        if response.status_code >= 400:
            raise AppException(status_code=503, detail="OpenAI provider unavailable")

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))
        estimated_cost = Decimal(prompt_tokens + completion_tokens) * Decimal(
            "0.000002"
        )

        return AIProviderResult(
            content_by_type=self._parse_json(content, content_types),
            model=model,
            cost_usd=estimated_cost,
            latency_ms=latency_ms,
        )


class OpenRouterProvider(OpenAIProvider):
    provider_name = "openrouter"

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        content_types: list[str],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AIProviderResult:
        self._base_url = self._base_url or "https://openrouter.ai/api"
        return await super().generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            content_types=content_types,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )


class DeepSeekProvider(OpenAIProvider):
    provider_name = "deepseek"

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        content_types: list[str],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AIProviderResult:
        self._base_url = self._base_url or "https://api.deepseek.com"
        return await super().generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            content_types=content_types,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )


class ClaudeProvider(_BaseHTTPProvider):
    provider_name = "claude"

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        content_types: list[str],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AIProviderResult:
        endpoint = (self._base_url or "https://api.anthropic.com") + "/v1/messages"
        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                endpoint,
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "system": system_prompt,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"{user_prompt}\n\n{self._json_instruction(content_types)}",
                        }
                    ],
                },
            )
        latency_ms = int((time.perf_counter() - start) * 1000)
        if response.status_code >= 400:
            raise AppException(status_code=503, detail="Claude provider unavailable")

        data = response.json()
        content = data["content"][0]["text"]
        return AIProviderResult(
            content_by_type=self._parse_json(content, content_types),
            model=model,
            cost_usd=Decimal("0"),
            latency_ms=latency_ms,
        )


class GeminiProvider(_BaseHTTPProvider):
    provider_name = "gemini"

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        content_types: list[str],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AIProviderResult:
        base = self._base_url or "https://generativelanguage.googleapis.com"
        endpoint = f"{base}/v1beta/models/{model}:generateContent"

        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                endpoint,
                params={"key": self._api_key},
                json={
                    "system_instruction": {
                        "parts": [{"text": system_prompt}],
                    },
                    "generationConfig": {
                        "temperature": temperature,
                        "maxOutputTokens": max_tokens,
                    },
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": f"{user_prompt}\n\n{self._json_instruction(content_types)}"
                                }
                            ]
                        }
                    ],
                },
            )
        latency_ms = int((time.perf_counter() - start) * 1000)
        if response.status_code >= 400:
            raise AppException(status_code=503, detail="Gemini provider unavailable")

        data = response.json()
        content = data["candidates"][0]["content"]["parts"][0]["text"]
        return AIProviderResult(
            content_by_type=self._parse_json(content, content_types),
            model=model,
            cost_usd=Decimal("0"),
            latency_ms=latency_ms,
        )


class ProviderFactory:
    def __init__(self) -> None:
        self._clients: dict[tuple[str, str, str], AIProvider] = {}

    def get_provider(
        self, *, provider_name: str, api_key: str, model: str, base_url: str | None
    ) -> AIProvider:
        cache_key = (provider_name, model, base_url or "")
        if cache_key in self._clients:
            return self._clients[cache_key]

        provider: AIProvider
        if provider_name == "openai":
            provider = OpenAIProvider(api_key=api_key, base_url=base_url)
        elif provider_name == "gemini":
            provider = GeminiProvider(api_key=api_key, base_url=base_url)
        elif provider_name == "claude":
            provider = ClaudeProvider(api_key=api_key, base_url=base_url)
        elif provider_name == "deepseek":
            provider = DeepSeekProvider(api_key=api_key, base_url=base_url)
        elif provider_name == "openrouter":
            provider = OpenRouterProvider(api_key=api_key, base_url=base_url)
        else:
            raise AppException(status_code=422, detail="AI provider not supported")

        self._clients[cache_key] = provider
        return provider
