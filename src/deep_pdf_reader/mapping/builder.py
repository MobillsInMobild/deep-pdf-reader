from __future__ import annotations

import json
import re
from collections import OrderedDict
from typing import Any

from deep_pdf_reader.models import (
    DocumentFingerprint,
    DocumentInfo,
    DocumentMap,
    PageMapEntry,
    ParsedDocument,
    SectionEntry,
)
from deep_pdf_reader.providers.base import TextModel


_NUMERIC_DETAIL = re.compile(
    r"(?<![A-Za-z])(?:[$€£¥]\s*)?\(?[+-]?\d[\d,.]*(?:\s*(?:%|percent|million|billion|trillion))?\)?",
    re.IGNORECASE,
)


class MapBuilder:
    """Build an untrusted, navigation-only map from parsed pages."""

    def __init__(self, text_model: TextModel) -> None:
        self._text_model = text_model

    def build(
        self,
        document: ParsedDocument,
        fingerprint: DocumentFingerprint,
        document_id: str,
    ) -> DocumentMap:
        current_path: list[str] = []
        mapped_pages: list[PageMapEntry] = []
        for page in document.pages:
            for heading in page.headings:
                level = max(1, min(3, heading.level))
                if level == 1:
                    current_path = [heading.text]
                elif len(current_path) >= level - 1:
                    current_path = current_path[: level - 1] + [heading.text]
                elif current_path:
                    current_path.append(heading.text)
                else:
                    current_path = [heading.text]

            metadata = self._navigation_metadata(
                text=page.text,
                headings=[heading.text for heading in page.headings],
            )
            mapped_pages.append(
                PageMapEntry(
                    page=page.page,
                    section_path=tuple(current_path),
                    summary=self._sanitize_summary(metadata.get("summary", "")),
                    keywords=self._sanitize_terms(metadata.get("keywords", []), 12),
                    entities=self._sanitize_terms(metadata.get("entities", []), 10),
                    has_table=page.has_table,
                    has_chart=page.has_chart,
                    has_image=page.has_image,
                )
            )

        sections = self._sections(mapped_pages)
        return DocumentMap(
            document=DocumentInfo(
                path=str(document.path),
                title=document.title,
                page_count=document.page_count,
                document_id=document_id,
                fingerprint=fingerprint,
            ),
            sections=sections,
            pages=tuple(mapped_pages),
        )

    def _navigation_metadata(self, text: str, headings: list[str]) -> dict[str, Any]:
        prompt = (
            "Create navigation-only metadata for one PDF page. Do not state or "
            "copy specific amounts, dates, percentages, units, or numeric facts. "
            "Return JSON with summary, keywords, and entities. The summary must "
            "only describe topics that could help locate evidence.\n\n"
            "NAVIGATION_INPUT_JSON:\n"
            + json.dumps(
                {"text": text[:12000], "headings": headings}, ensure_ascii=False
            )
        )
        raw = self._text_model.generate(
            prompt,
            system_prompt=(
                "You build an untrusted document navigation index. Never answer "
                "questions or turn extracted numbers into facts."
            ),
        )
        parsed = json.loads(_strip_json_fence(raw))
        if not isinstance(parsed, dict):
            raise ValueError("TextModel navigation response must be a JSON object")
        return parsed

    @staticmethod
    def _sanitize_summary(value: Any) -> str:
        compact = " ".join(str(value).split())[:500]
        return _NUMERIC_DETAIL.sub("[numeric detail omitted]", compact)

    @staticmethod
    def _sanitize_terms(values: Any, limit: int) -> tuple[str, ...]:
        if not isinstance(values, list):
            return ()
        terms: list[str] = []
        seen: set[str] = set()
        for raw_value in values:
            term = " ".join(str(raw_value).split()).strip(" ,.;:")
            normalized = term.casefold()
            if (
                not term
                or _NUMERIC_DETAIL.search(term)
                or normalized in seen
                or len(term) > 100
            ):
                continue
            terms.append(term)
            seen.add(normalized)
            if len(terms) >= limit:
                break
        return tuple(terms)

    @staticmethod
    def _sections(pages: list[PageMapEntry]) -> tuple[SectionEntry, ...]:
        grouped: OrderedDict[tuple[str, ...], list[int]] = OrderedDict()
        for page in pages:
            grouped.setdefault(page.section_path, []).append(page.page)
        return tuple(
            SectionEntry(
                path=path,
                pages=tuple(page_numbers),
                start_page=min(page_numbers),
                end_page=max(page_numbers),
            )
            for path, page_numbers in grouped.items()
            if path
        )


def _strip_json_fence(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped
