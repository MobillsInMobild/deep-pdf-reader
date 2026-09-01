from __future__ import annotations

import json
import re
from collections import Counter


_STOPWORDS = {
    "about",
    "after",
    "also",
    "and",
    "are",
    "because",
    "been",
    "before",
    "contains",
    "for",
    "from",
    "into",
    "its",
    "page",
    "that",
    "the",
    "their",
    "this",
    "through",
    "was",
    "were",
    "with",
}


class DeterministicTextModel:
    """Offline navigation-metadata provider used by the CLI and tests."""

    input_marker = "NAVIGATION_INPUT_JSON:"

    def generate(self, prompt: str, *, system_prompt: str | None = None) -> str:
        del system_prompt
        marker_index = prompt.rfind(self.input_marker)
        if marker_index < 0:
            raise ValueError("DeterministicTextModel received an unknown prompt")
        payload = json.loads(prompt[marker_index + len(self.input_marker) :].strip())
        text = " ".join(str(payload.get("text", "")).split())
        headings = [str(value) for value in payload.get("headings", [])]
        keywords = self._keywords(" ".join(headings) + " " + text)
        entities = self._entities(text, headings)
        topics = keywords[:4] or ["document content"]
        summary = "Contains discussion of " + ", ".join(topics) + "."
        return json.dumps(
            {"summary": summary, "keywords": keywords, "entities": entities},
            ensure_ascii=False,
        )

    @staticmethod
    def _keywords(text: str) -> list[str]:
        ascii_words = re.findall(r"[A-Za-z][A-Za-z_-]{2,}", text.casefold())
        cjk_runs = re.findall(r"[\u3400-\u9fff]{2,}", text)
        cjk_terms: list[str] = []
        for run in cjk_runs:
            if len(run) <= 6:
                cjk_terms.append(run)
            else:
                cjk_terms.extend(run[index : index + 2] for index in range(len(run) - 1))
        counts = Counter(
            word
            for word in [*ascii_words, *cjk_terms]
            if word not in _STOPWORDS and not any(character.isdigit() for character in word)
        )
        return [word for word, _ in counts.most_common(12)]

    @staticmethod
    def _entities(text: str, headings: list[str]) -> list[str]:
        candidates = re.findall(
            r"\b(?:[A-Z][A-Za-z&.-]+(?:\s+|$)){1,5}", " ".join(headings) + " " + text
        )
        entities: list[str] = []
        for candidate in candidates:
            value = " ".join(candidate.split()).strip(" .,-")
            if len(value) >= 3 and value not in entities and not re.search(r"\d", value):
                entities.append(value)
        return entities[:10]
