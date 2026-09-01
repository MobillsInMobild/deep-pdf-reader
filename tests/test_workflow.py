from __future__ import annotations

from pathlib import Path

from deep_pdf_reader.inspection.base import MockPageInspector
from deep_pdf_reader.mapping.builder import MapBuilder
from deep_pdf_reader.models import EvidenceItem, EvidenceResult
from deep_pdf_reader.parsers.pymupdf import PyMuPDFParser
from deep_pdf_reader.providers.mock import DeterministicTextModel
from deep_pdf_reader.rendering.renderer import PageRenderer
from deep_pdf_reader.workflow import DeepPdfReader


def test_end_to_end_ask_searches_renders_and_inspects(
    sample_pdf: Path, tmp_path: Path
) -> None:
    inspector = MockPageInspector(
        EvidenceResult(
            answer=(
                "Operating cash flow declined because collections slowed and "
                "inventory purchases increased."
            ),
            evidence=(
                EvidenceItem(
                    page=2,
                    detail="The original page identifies both working-capital drivers.",
                ),
            ),
            confidence="high",
        )
    )
    reader = DeepPdfReader(
        parser=PyMuPDFParser(),
        map_builder=MapBuilder(DeterministicTextModel()),
        inspector=inspector,
        renderer=PageRenderer(dpi=96),
        cache_root=tmp_path / "cache",
        candidate_pages=3,
    )

    result = reader.ask(sample_pdf, "Why did operating cash flow decline?")

    assert result.evidence_result.confidence == "high"
    assert result.evidence_result.evidence[0].page == 2
    assert {candidate.page for candidate in result.candidates} >= {2, 3}
    assert 3 <= len(result.page_images) <= 8
    assert all(path.is_file() for path in result.page_images)
    assert inspector.trace.page_images[0] == result.page_images
    assert reader.build_map(sample_pdf).reused is True
