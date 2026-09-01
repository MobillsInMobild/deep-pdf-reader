from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pymupdf as fitz


class PageRenderer:
    def __init__(self, *, dpi: int = 150) -> None:
        if dpi < 72:
            raise ValueError("Rendering DPI must be at least 72")
        self._dpi = dpi

    def render(
        self,
        pdf_path: Path,
        pages: Iterable[int],
        output_dir: Path,
    ) -> tuple[Path, ...]:
        requested = tuple(dict.fromkeys(int(page) for page in pages))
        if not requested:
            return ()
        source_path = pdf_path.expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        rendered: list[Path] = []
        with fitz.open(source_path) as document:
            for page_number in requested:
                if not 1 <= page_number <= document.page_count:
                    raise ValueError(
                        f"Page {page_number} is outside 1-{document.page_count}"
                    )
                output_path = output_dir / f"page-{page_number:04d}.png"
                if not output_path.is_file():
                    page = document.load_page(page_number - 1)
                    scale = self._dpi / 72.0
                    pixmap = page.get_pixmap(
                        matrix=fitz.Matrix(scale, scale), alpha=False
                    )
                    pixmap.save(output_path)
                rendered.append(output_path)
        return tuple(rendered)
