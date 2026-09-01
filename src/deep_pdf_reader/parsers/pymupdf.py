from __future__ import annotations

import contextlib
import io
import re
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pymupdf as fitz

from deep_pdf_reader.models import HeadingClue, ParsedDocument, ParsedPage


@dataclass(frozen=True, slots=True)
class _Span:
    page: int
    text: str
    size: float
    bold: bool
    y0: float


class PyMuPDFParser:
    """Extract page text and conservative layout clues with PyMuPDF."""

    def parse(self, path: Path) -> ParsedDocument:
        pdf_path = path.expanduser().resolve()
        if not pdf_path.is_file():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        with fitz.open(pdf_path) as document:
            if document.needs_pass:
                raise ValueError(f"Password-protected PDF is not supported: {pdf_path}")

            page_data: list[tuple[str, list[_Span], bool, bool, bool]] = []
            all_heading_sizes: list[float] = []
            for page_index, page in enumerate(document):
                page_number = page_index + 1
                text = page.get_text("text", sort=True).strip()
                spans = self._extract_spans(page, page_number)
                heading_spans = self._heading_candidates(spans)
                all_heading_sizes.extend(span.size for span in heading_spans)
                has_table, drawing_count = self._table_clue(page)
                has_image = bool(page.get_images(full=True))
                lower_text = text.casefold()
                has_chart = (
                    not has_table
                    and (
                        drawing_count >= 6
                        or has_image
                        and any(word in lower_text for word in ("chart", "figure", "graph"))
                    )
                )
                page_data.append(
                    (text, heading_spans, has_table, has_chart, has_image)
                )

            size_levels = self._size_levels(all_heading_sizes)
            pages = tuple(
                ParsedPage(
                    page=index + 1,
                    text=text,
                    headings=tuple(
                        HeadingClue(
                            text=span.text,
                            level=size_levels.get(round(span.size, 1), 3),
                            font_size=span.size,
                        )
                        for span in sorted(spans, key=lambda value: value.y0)
                    ),
                    has_table=has_table,
                    has_chart=has_chart,
                    has_image=has_image,
                )
                for index, (text, spans, has_table, has_chart, has_image) in enumerate(
                    page_data
                )
            )
            metadata = document.metadata or {}
            title = str(metadata.get("title") or "").strip() or pdf_path.stem
            return ParsedDocument(
                path=pdf_path,
                title=title,
                page_count=document.page_count,
                pages=pages,
            )

    @staticmethod
    def _extract_spans(page: fitz.Page, page_number: int) -> list[_Span]:
        page_dict: dict[str, Any] = page.get_text("dict", sort=True)
        spans: list[_Span] = []
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for raw_span in line.get("spans", []):
                    text = " ".join(str(raw_span.get("text", "")).split())
                    if not text:
                        continue
                    font = str(raw_span.get("font", "")).casefold()
                    bbox = raw_span.get("bbox") or (0, 0, 0, 0)
                    spans.append(
                        _Span(
                            page=page_number,
                            text=text,
                            size=float(raw_span.get("size", 0.0)),
                            bold="bold" in font or "black" in font,
                            y0=float(bbox[1]),
                        )
                    )
        return spans

    @staticmethod
    def _heading_candidates(spans: list[_Span]) -> list[_Span]:
        body_sizes = [span.size for span in spans if span.size > 0]
        if not body_sizes:
            return []
        median_size = statistics.median(body_sizes)
        candidates: list[_Span] = []
        seen: set[tuple[str, int]] = set()
        for span in spans:
            compact = span.text.strip(" -\t")
            key = (compact.casefold(), round(span.y0))
            is_short = 2 <= len(compact) <= 120
            is_not_number = not re.fullmatch(r"[\d\W_]+", compact)
            visually_distinct = span.size >= median_size * 1.16 or (
                span.bold and span.size >= median_size * 1.05
            )
            if is_short and is_not_number and visually_distinct and key not in seen:
                candidates.append(span)
                seen.add(key)
        return candidates

    @staticmethod
    def _size_levels(sizes: list[float]) -> dict[float, int]:
        distinct = sorted({round(size, 1) for size in sizes}, reverse=True)
        return {size: min(index + 1, 3) for index, size in enumerate(distinct)}

    @staticmethod
    def _table_clue(page: fitz.Page) -> tuple[bool, int]:
        drawings = page.get_drawings()
        drawing_count = len(drawings)
        find_tables = getattr(page, "find_tables", None)
        if callable(find_tables):
            try:
                # Recent PyMuPDF versions print an optional layout-package hint.
                # The MVP deliberately avoids that extra dependency.
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
                    io.StringIO()
                ):
                    result = find_tables()
                if getattr(result, "tables", []):
                    return True, drawing_count
            except Exception:
                # Table detection is a navigation hint; extraction must remain usable.
                pass
        words = page.get_text("words", sort=True)
        rows: dict[int, int] = {}
        for word in words:
            row_key = round(float(word[1]) / 4)
            rows[row_key] = rows.get(row_key, 0) + 1
        tabular_rows = sum(count >= 3 for count in rows.values())
        return drawing_count >= 4 and tabular_rows >= 2, drawing_count
