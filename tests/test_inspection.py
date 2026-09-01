from __future__ import annotations

from pathlib import Path

from deep_pdf_reader.inspection.base import MockPageInspector
from deep_pdf_reader.models import EvidenceItem, EvidenceResult


def test_mock_page_inspector_returns_injected_result_and_records_call() -> None:
    expected = EvidenceResult(
        answer="Collections slowed.",
        evidence=(EvidenceItem(page=2, detail="The source page states the cause."),),
        confidence="high",
    )
    inspector = MockPageInspector(expected)
    images = [Path("page-0002.png")]

    actual = inspector.inspect("Why?", images)

    assert actual == expected
    assert inspector.trace.questions == ["Why?"]
    assert inspector.trace.page_images == [(Path("page-0002.png"),)]
