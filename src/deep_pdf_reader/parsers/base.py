from __future__ import annotations

from pathlib import Path
from typing import Protocol

from deep_pdf_reader.models import ParsedDocument


class DocumentParser(Protocol):
    def parse(self, path: Path) -> ParsedDocument:
        """Parse a document into page-level content and navigation clues."""
