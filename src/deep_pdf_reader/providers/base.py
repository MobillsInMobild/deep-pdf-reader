from __future__ import annotations

from typing import Protocol


class TextModel(Protocol):
    def generate(self, prompt: str, *, system_prompt: str | None = None) -> str:
        """Return text generated from a prompt."""
