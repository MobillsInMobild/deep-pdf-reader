from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class HeadingClue:
    text: str
    level: int
    font_size: float


@dataclass(frozen=True, slots=True)
class ParsedPage:
    page: int
    text: str
    headings: tuple[HeadingClue, ...] = ()
    has_table: bool = False
    has_chart: bool = False
    has_image: bool = False


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    path: Path
    title: str
    page_count: int
    pages: tuple[ParsedPage, ...]


@dataclass(frozen=True, slots=True)
class DocumentFingerprint:
    path: str
    size: int
    mtime_ns: int
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "size": self.size,
            "mtime_ns": self.mtime_ns,
            "sha256": self.sha256,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> DocumentFingerprint:
        return cls(
            path=str(value["path"]),
            size=int(value["size"]),
            mtime_ns=int(value["mtime_ns"]),
            sha256=str(value["sha256"]),
        )


@dataclass(frozen=True, slots=True)
class DocumentInfo:
    path: str
    title: str
    page_count: int
    document_id: str
    fingerprint: DocumentFingerprint


@dataclass(frozen=True, slots=True)
class SectionEntry:
    path: tuple[str, ...]
    pages: tuple[int, ...]
    start_page: int
    end_page: int

    @property
    def display_name(self) -> str:
        return " > ".join(self.path) if self.path else "Document"


@dataclass(frozen=True, slots=True)
class PageMapEntry:
    page: int
    section_path: tuple[str, ...]
    summary: str
    keywords: tuple[str, ...]
    entities: tuple[str, ...]
    has_table: bool
    has_chart: bool
    has_image: bool


@dataclass(frozen=True, slots=True)
class DocumentMap:
    document: DocumentInfo
    sections: tuple[SectionEntry, ...]
    pages: tuple[PageMapEntry, ...]
    schema_version: int = 1

    def page(self, page_number: int) -> PageMapEntry:
        for entry in self.pages:
            if entry.page == page_number:
                return entry
        raise KeyError(f"Page {page_number} is not present in the document map")


@dataclass(frozen=True, slots=True)
class CandidatePage:
    page: int
    section_path: tuple[str, ...]
    score: float
    reasons: tuple[str, ...]
    summary: str


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    page: int
    detail: str


@dataclass(frozen=True, slots=True)
class EvidenceResult:
    answer: str
    evidence: tuple[EvidenceItem, ...] = ()
    confidence: str = "low"
    insufficient_evidence: tuple[str, ...] = ()
    needs_more_evidence: bool = False
    suggested_queries: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class BuildMapResult:
    document_map: DocumentMap
    map_path: Path
    document_dir: Path
    reused: bool


@dataclass(frozen=True, slots=True)
class SearchResult:
    document_map: DocumentMap
    candidates: tuple[CandidatePage, ...]
    map_reused: bool


@dataclass(frozen=True, slots=True)
class AskResult:
    evidence_result: EvidenceResult
    candidates: tuple[CandidatePage, ...]
    page_images: tuple[Path, ...]
    map_reused: bool


@dataclass(slots=True)
class InspectionTrace:
    """Mutable call trace used by deterministic inspectors in tests."""

    questions: list[str] = field(default_factory=list)
    page_images: list[tuple[Path, ...]] = field(default_factory=list)
