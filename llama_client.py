"""Client for llama.cpp OpenAI-compatible server with vision support."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

from openai import OpenAI


DEFAULT_BASE_URL = os.getenv("LLAMA_BASE_URL", "http://localhost:8080/v1")
DEFAULT_MODEL = os.getenv("LLAMA_MODEL")
DEFAULT_TEMPERATURE = float(os.getenv("LLAMA_TEMPERATURE", "0"))
DEFAULT_MAX_TOKENS = int(os.getenv("LLAMA_MAX_TOKENS", "2048"))


@dataclass
class LlamaConfig:
    base_url: str = DEFAULT_BASE_URL
    model: Optional[str] = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS


class LlamaClient:
    """Thin wrapper around the OpenAI client for llama.cpp servers."""

    def __init__(self, config: Optional[LlamaConfig] = None) -> None:
        self.config = config or LlamaConfig()
        self._client = OpenAI(base_url=self.config.base_url, api_key="dummy-key")

    def _resolve_model(self) -> str:
        if self.config.model:
            return self.config.model

        try:
            models_resp = self._client.models.list()
            if models_resp.data:
                return models_resp.data[0].id
        except Exception:
            pass
        return ""

    def chat_markdown(self, prompt: str, images: List[str]) -> str:
        messages = [
            {
                "role": "user",
                "content": self._build_content(prompt, images),
            }
        ]
        response = self._client.chat.completions.create(
            model=self._resolve_model(),
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        return response.choices[0].message.content or ""

    def chat_json(self, prompt: str, images: List[str]) -> str:
        messages = [
            {
                "role": "user",
                "content": self._build_content(prompt, images),
            }
        ]
        response = self._client.chat.completions.create(
            model=self._resolve_model(),
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or ""

    @staticmethod
    def _build_content(prompt: str, images: List[str]):
        content = [{"type": "text", "text": prompt}]
        for image_data_url in images:
            content.append({
                "type": "image_url",
                "image_url": {"url": image_data_url},
            })
        return content
