from __future__ import annotations

from pathlib import Path
from typing import Protocol

from deep_pdf_reader.models import EvidenceResult, InspectionTrace


class PageInspector(Protocol):
    def inspect(self, question: str, page_images: list[Path]) -> EvidenceResult:
        """Inspect original-page images and return structured evidence."""


class MockPageInspector:
    """Deterministic inspector for tests and provider-free CLI operation."""

    def __init__(self, result: EvidenceResult | None = None) -> None:
        self.trace = InspectionTrace()
        self._result = result or EvidenceResult(
            answer="No visual inspector is configured, so no factual answer was produced.",
            confidence="low",
            insufficient_evidence=(
                "Configure an OpenAI-compatible vision model to inspect source pages.",
            ),
        )

    def inspect(self, question: str, page_images: list[Path]) -> EvidenceResult:
        self.trace.questions.append(question)
        self.trace.page_images.append(tuple(page_images))
        return self._result
