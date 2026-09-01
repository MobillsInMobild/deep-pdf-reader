from __future__ import annotations

from pathlib import Path

from deep_pdf_reader.parsers.pymupdf import PyMuPDFParser


def test_pymupdf_extracts_page_text_headings_and_table(sample_pdf: Path) -> None:
    document = PyMuPDFParser().parse(sample_pdf)

    assert document.title == "Deep Reader Test Report"
    assert document.page_count == 4
    assert "Acme Corporation" in document.pages[0].text
    assert "Operating cash flow declined" in document.pages[1].text
    assert [heading.level for heading in document.pages[1].headings] == [1, 2]
    assert [heading.text for heading in document.pages[1].headings] == [
        "2. Management Discussion",
        "2.1 Liquidity and Cash Flow",
    ]
    assert document.pages[2].has_table is True
