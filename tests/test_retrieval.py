from __future__ import annotations

from deep_pdf_reader.models import (
    DocumentFingerprint,
    DocumentInfo,
    DocumentMap,
    PageMapEntry,
    SectionEntry,
)
from deep_pdf_reader.retrieval.search import MapSearcher


def test_keyword_retrieval_and_section_boost(document_map: DocumentMap) -> None:
    candidates = MapSearcher().search(
        document_map, "Why did operating cash flow decline?", limit=3
    )

    assert {candidate.page for candidate in candidates} >= {2, 3}
    relevant = [candidate for candidate in candidates if candidate.page in {2, 3}]
    assert any(
        "keyword match" in reason
        for candidate in relevant
        for reason in candidate.reasons
    )
    assert all(
        any("section/title boost" in reason for reason in candidate.reasons)
        for candidate in relevant
    )


def test_neighboring_page_expansion_keeps_table_continuation() -> None:
    fingerprint = DocumentFingerprint("test.pdf", 1, 1, "abc")
    section = ("Management Discussion", "Liquidity")
    document_map = DocumentMap(
        document=DocumentInfo("test.pdf", "Test", 4, "doc", fingerprint),
        sections=(SectionEntry(section, (2, 3), 2, 3),),
        pages=(
            PageMapEntry(1, ("Overview",), "company overview", ("company",), (), False, False, False),
            PageMapEntry(
                2,
                section,
                "Contains discussion of operating cash flow decline.",
                ("operating", "cash", "flow", "decline"),
                ("Operating Cash Flow",),
                False,
                False,
                False,
            ),
            PageMapEntry(
                3,
                section,
                "Contains supporting cash flow table.",
                ("supporting", "table"),
                (),
                True,
                False,
                False,
            ),
            PageMapEntry(4, ("Risks",), "supply risks", ("supply",), (), False, False, False),
        ),
    )

    candidates = MapSearcher().search(
        document_map, "operating cash flow decline", limit=3
    )

    assert [candidate.page for candidate in candidates[:2]] == [2, 3]
    page_three = next(candidate for candidate in candidates if candidate.page == 3)
    assert any("neighbor of page 2" in reason for reason in page_three.reasons)
