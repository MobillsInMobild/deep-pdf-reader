from __future__ import annotations

from typing import Any

from deep_pdf_reader.models import (
    DocumentFingerprint,
    DocumentInfo,
    DocumentMap,
    PageMapEntry,
    SectionEntry,
)


def document_map_to_dict(document_map: DocumentMap) -> dict[str, Any]:
    return {
        "schema_version": document_map.schema_version,
        "document": {
            "path": document_map.document.path,
            "title": document_map.document.title,
            "page_count": document_map.document.page_count,
            "document_id": document_map.document.document_id,
            "fingerprint": document_map.document.fingerprint.to_dict(),
        },
        "sections": [
            {
                "path": list(section.path),
                "pages": list(section.pages),
                "start_page": section.start_page,
                "end_page": section.end_page,
            }
            for section in document_map.sections
        ],
        "pages": [
            {
                "page": page.page,
                "section_path": list(page.section_path),
                "summary": page.summary,
                "keywords": list(page.keywords),
                "entities": list(page.entities),
                "has_table": page.has_table,
                "has_chart": page.has_chart,
                "has_image": page.has_image,
            }
            for page in document_map.pages
        ],
    }


def document_map_from_dict(value: dict[str, Any]) -> DocumentMap:
    schema_version = int(value.get("schema_version", 1))
    if schema_version != 1:
        raise ValueError(f"Unsupported map schema version: {schema_version}")
    raw_document = value["document"]
    document = DocumentInfo(
        path=str(raw_document["path"]),
        title=str(raw_document["title"]),
        page_count=int(raw_document["page_count"]),
        document_id=str(raw_document["document_id"]),
        fingerprint=DocumentFingerprint.from_dict(raw_document["fingerprint"]),
    )
    sections = tuple(
        SectionEntry(
            path=tuple(str(item) for item in raw["path"]),
            pages=tuple(int(item) for item in raw["pages"]),
            start_page=int(raw["start_page"]),
            end_page=int(raw["end_page"]),
        )
        for raw in value.get("sections", [])
    )
    pages = tuple(
        PageMapEntry(
            page=int(raw["page"]),
            section_path=tuple(str(item) for item in raw.get("section_path", [])),
            summary=str(raw.get("summary", "")),
            keywords=tuple(str(item) for item in raw.get("keywords", [])),
            entities=tuple(str(item) for item in raw.get("entities", [])),
            has_table=bool(raw.get("has_table", False)),
            has_chart=bool(raw.get("has_chart", False)),
            has_image=bool(raw.get("has_image", False)),
        )
        for raw in value.get("pages", [])
    )
    if document.page_count != len(pages):
        raise ValueError(
            "Map page count mismatch: "
            f"document declares {document.page_count}, map contains {len(pages)}"
        )
    return DocumentMap(
        document=document,
        sections=sections,
        pages=pages,
        schema_version=schema_version,
    )
