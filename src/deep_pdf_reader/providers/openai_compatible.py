from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class OpenAICompatibleClient:
    base_url: str
    api_key: str
    timeout: float = 60.0

    def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        endpoint = self.base_url.rstrip("/") + "/chat/completions"
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"OpenAI-compatible endpoint returned HTTP {exc.code}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenAI-compatible request failed: {exc.reason}") from exc


@dataclass(frozen=True, slots=True)
class OpenAICompatibleTextModel:
    base_url: str
    api_key: str
    model: str
    timeout: float = 60.0

    def generate(self, prompt: str, *, system_prompt: str | None = None) -> str:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        response = OpenAICompatibleClient(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout,
        ).chat_completion(
            {
                "model": self.model,
                "messages": messages,
                "temperature": 0,
                "response_format": {"type": "json_object"},
            }
        )
        try:
            return str(response["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Malformed OpenAI-compatible chat response") from exc
