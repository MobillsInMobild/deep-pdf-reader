from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from deep_pdf_reader.mapping.builder import MapBuilder
from deep_pdf_reader.mapping.schema import document_map_from_dict, document_map_to_dict
from deep_pdf_reader.models import BuildMapResult, DocumentFingerprint
from deep_pdf_reader.parsers.base import DocumentParser


@dataclass(frozen=True, slots=True)
class CachePaths:
    document_dir: Path
    map_path: Path
    pages_dir: Path


class DocumentMapStore:
    def __init__(
        self,
        parser: DocumentParser,
        builder: MapBuilder,
        cache_root: Path | None = None,
    ) -> None:
        self._parser = parser
        self._builder = builder
        self._cache_root = cache_root

    def load_or_build(self, path: Path, *, force: bool = False) -> BuildMapResult:
        pdf_path = path.expanduser().resolve()
        fingerprint = fingerprint_document(pdf_path)
        document_id = document_id_for(fingerprint)
        paths = self.cache_paths(pdf_path, document_id)
        if paths.map_path.is_file() and not force:
            document_map = document_map_from_dict(
                json.loads(paths.map_path.read_text(encoding="utf-8"))
            )
            if document_map.document.fingerprint == fingerprint:
                return BuildMapResult(
                    document_map=document_map,
                    map_path=paths.map_path,
                    document_dir=paths.document_dir,
                    reused=True,
                )

        parsed = self._parser.parse(pdf_path)
        document_map = self._builder.build(parsed, fingerprint, document_id)
        paths.document_dir.mkdir(parents=True, exist_ok=True)
        temporary_path = paths.map_path.with_suffix(".json.tmp")
        temporary_path.write_text(
            json.dumps(
                document_map_to_dict(document_map),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(paths.map_path)
        return BuildMapResult(
            document_map=document_map,
            map_path=paths.map_path,
            document_dir=paths.document_dir,
            reused=False,
        )

    def cache_paths(self, pdf_path: Path, document_id: str) -> CachePaths:
        root = self._cache_root or pdf_path.resolve().parent / ".deep-pdf-reader"
        document_dir = root / document_id
        return CachePaths(
            document_dir=document_dir,
            map_path=document_dir / "map.json",
            pages_dir=document_dir / "pages",
        )


def fingerprint_document(path: Path) -> DocumentFingerprint:
    pdf_path = path.expanduser().resolve()
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    stat = pdf_path.stat()
    digest = hashlib.sha256()
    with pdf_path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return DocumentFingerprint(
        path=str(pdf_path),
        size=stat.st_size,
        mtime_ns=stat.st_mtime_ns,
        sha256=digest.hexdigest(),
    )


def document_id_for(fingerprint: DocumentFingerprint) -> str:
    identity = json.dumps(
        fingerprint.to_dict(), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(identity).hexdigest()[:20]
