from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True, slots=True)
class Settings:
    cache_dir: Path | None = None
    base_url: str = "https://api.openai.com/v1"
    api_key: str | None = None
    text_model: str | None = None
    vision_model: str | None = None
    request_timeout: float = 60.0
    candidate_pages: int = 5

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        values = os.environ if env is None else env
        cache_value = values.get("DEEP_PDF_READER_CACHE_DIR")
        candidate_pages = _bounded_int(
            values.get("DEEP_PDF_READER_CANDIDATE_PAGES", "5"), 3, 8
        )
        return cls(
            cache_dir=Path(cache_value).expanduser() if cache_value else None,
            base_url=values.get(
                "DEEP_PDF_READER_BASE_URL", "https://api.openai.com/v1"
            ),
            api_key=values.get("DEEP_PDF_READER_API_KEY"),
            text_model=values.get("DEEP_PDF_READER_TEXT_MODEL"),
            vision_model=values.get("DEEP_PDF_READER_VISION_MODEL"),
            request_timeout=float(
                values.get("DEEP_PDF_READER_REQUEST_TIMEOUT", "60")
            ),
            candidate_pages=candidate_pages,
        )


def _bounded_int(raw_value: str, minimum: int, maximum: int) -> int:
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"Expected an integer, got {raw_value!r}") from exc
    return max(minimum, min(maximum, value))
