"""LLM Provider Abstraction

This module provides a thin abstraction over different LLM backends.

Supported providers:
- ollama: Local Ollama server (recommended for easy local dev)
- openai: OpenAI Chat Completions (legacy/optional)

All callers should request a JSON object response and this client will
attempt to parse/repair JSON when models return extra text.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()


def _extract_first_json_object(text: str) -> Optional[dict[str, Any]]:
    """Best-effort extraction of the first JSON object from a string."""
    if not text:
        return None

    text = text.strip()

    # Fast path
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    # Find the first balanced {...} object.
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : i + 1]
                try:
                    parsed = json.loads(candidate)
                    if isinstance(parsed, dict):
                        return parsed
                except Exception:
                    return None

    return None


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    base_url: str
    timeout_seconds: float = 120.0


class LLMClient:
    async def generate_json(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> Optional[dict[str, Any]]:
        raise NotImplementedError


class OllamaLLMClient(LLMClient):
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        self._client = httpx.AsyncClient(timeout=cfg.timeout_seconds)

    async def generate_json(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> Optional[dict[str, Any]]:
        """Call Ollama /api/chat and return a parsed JSON object."""
        url = self.cfg.base_url.rstrip("/") + "/api/chat"
        payload = {
            "model": self.cfg.model,
            "stream": False,
            # Ollama supports forcing JSON with `format: "json"`.
            "format": "json",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert educational content creator. Always respond with valid JSON only (no extra text).",
                },
                {"role": "user", "content": prompt},
            ],
            "options": {
                "temperature": float(temperature),
                # Ollama uses num_predict as an approximate output token cap.
                "num_predict": int(max_tokens),
            },
        }

        try:
            resp = await self._client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

            # Expected: { message: { content: "..." } }
            content = (
                (data.get("message") or {}).get("content")
                if isinstance(data, dict)
                else None
            )
            if not content or not isinstance(content, str):
                logger.error("Ollama response missing message.content", response=data)
                return None

            parsed = _extract_first_json_object(content)
            if parsed is None:
                logger.error("Failed to parse Ollama JSON", content_preview=content[:500])
            return parsed

        except httpx.HTTPError as e:
            logger.error("Ollama HTTP error", error=str(e))
            return None
        except Exception as e:
            logger.error("Ollama call failed", error=str(e))
            return None


class OpenAILLMClient(LLMClient):
    def __init__(self, model: str):
        # Import here so local-only users don't need OpenAI for runtime
        from openai import AsyncOpenAI

        base_url = (getattr(settings, "openai_base_url", "") or "").strip()
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=base_url or None,
        )
        self.model = model

    async def generate_json(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> Optional[dict[str, Any]]:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert educational content creator. Always respond with valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            parsed = _extract_first_json_object(content or "")
            if parsed is None:
                logger.error("Failed to parse OpenAI JSON", content_preview=(content or "")[:500])
            return parsed
        except Exception as e:
            logger.error("OpenAI call failed", error=str(e))
            return None


def get_llm_client() -> LLMClient:
    provider = (getattr(settings, "llm_provider", "ollama") or "ollama").lower()

    if provider in {"openai", "openai_compat"}:
        return OpenAILLMClient(model=settings.openai_model)

    # Default: Ollama
    base_url = getattr(settings, "ollama_base_url", "http://localhost:11434")
    model = getattr(settings, "llm_model", "llama3.1")
    cfg = LLMConfig(provider="ollama", model=model, base_url=base_url)
    return OllamaLLMClient(cfg)
