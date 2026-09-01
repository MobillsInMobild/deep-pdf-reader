from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from deep_pdf_reader.mapping.builder import MapBuilder
from deep_pdf_reader.mapping.schema import document_map_from_dict, document_map_to_dict
from deep_pdf_reader.mapping.store import DocumentMapStore
from deep_pdf_reader.models import DocumentMap, ParsedDocument
from deep_pdf_reader.parsers.pymupdf import PyMuPDFParser
from deep_pdf_reader.providers.mock import DeterministicTextModel


def test_map_serialization_has_required_shape(document_map: DocumentMap) -> None:
    serialized = document_map_to_dict(document_map)
    restored = document_map_from_dict(json.loads(json.dumps(serialized)))

    assert set(serialized) == {"schema_version", "document", "sections", "pages"}
    assert set(serialized["document"]) >= {"path", "title", "page_count"}
    assert set(serialized["pages"][0]) >= {
        "page",
        "section_path",
        "summary",
        "keywords",
        "entities",
        "has_table",
        "has_chart",
        "has_image",
    }
    assert restored == document_map
    assert "12.83" not in " ".join(page.summary for page in restored.pages)
    assert restored.pages[1].section_path == (
        "2. Management Discussion",
        "2.1 Liquidity and Cash Flow",
    )
    assert restored.pages[2].section_path == restored.pages[1].section_path


@dataclass
class _CountingParser:
    delegate: PyMuPDFParser
    calls: int = 0

    def parse(self, path: Path) -> ParsedDocument:
        self.calls += 1
        return self.delegate.parse(path)


def test_unchanged_pdf_reuses_existing_map(sample_pdf: Path, tmp_path: Path) -> None:
    parser = _CountingParser(PyMuPDFParser())
    store = DocumentMapStore(
        parser,
        MapBuilder(DeterministicTextModel()),
        cache_root=tmp_path / "cache",
    )

    first = store.load_or_build(sample_pdf)
    second = store.load_or_build(sample_pdf)

    assert first.reused is False
    assert second.reused is True
    assert first.map_path == second.map_path
    assert parser.calls == 1
