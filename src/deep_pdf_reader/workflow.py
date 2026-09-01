from __future__ import annotations

from pathlib import Path

from deep_pdf_reader.config import Settings
from deep_pdf_reader.inspection.base import MockPageInspector, PageInspector
from deep_pdf_reader.inspection.openai_compatible import OpenAICompatiblePageInspector
from deep_pdf_reader.mapping.builder import MapBuilder
from deep_pdf_reader.mapping.store import DocumentMapStore
from deep_pdf_reader.models import AskResult, BuildMapResult, CandidatePage, SearchResult
from deep_pdf_reader.parsers.base import DocumentParser
from deep_pdf_reader.parsers.pymupdf import PyMuPDFParser
from deep_pdf_reader.providers.base import TextModel
from deep_pdf_reader.providers.mock import DeterministicTextModel
from deep_pdf_reader.providers.openai_compatible import OpenAICompatibleTextModel
from deep_pdf_reader.rendering.renderer import PageRenderer
from deep_pdf_reader.retrieval.search import MapSearcher


class DeepPdfReader:
    def __init__(
        self,
        *,
        parser: DocumentParser,
        map_builder: MapBuilder,
        inspector: PageInspector,
        cache_root: Path | None = None,
        renderer: PageRenderer | None = None,
        searcher: MapSearcher | None = None,
        candidate_pages: int = 5,
    ) -> None:
        self._store = DocumentMapStore(parser, map_builder, cache_root)
        self._inspector = inspector
        self._renderer = renderer or PageRenderer()
        self._searcher = searcher or MapSearcher()
        self._candidate_pages = max(3, min(8, candidate_pages))

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> DeepPdfReader:
        configured = settings or Settings.from_env()
        text_model: TextModel
        if configured.text_model:
            if not configured.api_key:
                raise ValueError(
                    "DEEP_PDF_READER_API_KEY is required when a text model is configured"
                )
            text_model = OpenAICompatibleTextModel(
                base_url=configured.base_url,
                api_key=configured.api_key,
                model=configured.text_model,
                timeout=configured.request_timeout,
            )
        else:
            text_model = DeterministicTextModel()

        inspector: PageInspector
        if configured.vision_model:
            if not configured.api_key:
                raise ValueError(
                    "DEEP_PDF_READER_API_KEY is required when a vision model is configured"
                )
            inspector = OpenAICompatiblePageInspector(
                base_url=configured.base_url,
                api_key=configured.api_key,
                model=configured.vision_model,
                timeout=configured.request_timeout,
            )
        else:
            inspector = MockPageInspector()
        return cls(
            parser=PyMuPDFParser(),
            map_builder=MapBuilder(text_model),
            inspector=inspector,
            cache_root=configured.cache_dir,
            candidate_pages=configured.candidate_pages,
        )

    def build_map(self, pdf_path: Path, *, force: bool = False) -> BuildMapResult:
        return self._store.load_or_build(pdf_path, force=force)

    def search(
        self, pdf_path: Path, question: str, *, limit: int | None = None
    ) -> SearchResult:
        build_result = self.build_map(pdf_path)
        candidates = self._searcher.search(
            build_result.document_map,
            question,
            limit=limit or self._candidate_pages,
        )
        return SearchResult(
            document_map=build_result.document_map,
            candidates=candidates,
            map_reused=build_result.reused,
        )

    def render(self, pdf_path: Path, pages: list[int]) -> tuple[Path, ...]:
        build_result = self.build_map(pdf_path)
        return self._renderer.render(
            Path(build_result.document_map.document.path),
            pages,
            build_result.document_dir / "pages",
        )

    def ask(
        self, pdf_path: Path, question: str, *, limit: int | None = None
    ) -> AskResult:
        initial_limit = max(3, min(8, limit or self._candidate_pages))
        build_result = self.build_map(pdf_path)
        candidates = list(
            self._searcher.search(
                build_result.document_map, question, limit=initial_limit
            )
        )
        page_images = list(
            self._renderer.render(
                Path(build_result.document_map.document.path),
                [candidate.page for candidate in candidates],
                build_result.document_dir / "pages",
            )
        )
        evidence_result = self._inspector.inspect(question, page_images)

        if evidence_result.needs_more_evidence and len(candidates) < 8:
            remaining = 8 - len(candidates)
            follow_up_question = " ".join(evidence_result.suggested_queries).strip()
            second_candidates = self._searcher.search(
                build_result.document_map,
                follow_up_question or question,
                limit=remaining,
                exclude_pages=frozenset(candidate.page for candidate in candidates),
            )
            if second_candidates:
                second_candidates = second_candidates[:remaining]
                candidates.extend(second_candidates)
                page_images = list(
                    self._renderer.render(
                        Path(build_result.document_map.document.path),
                        [candidate.page for candidate in candidates],
                        build_result.document_dir / "pages",
                    )
                )
                evidence_result = self._inspector.inspect(question, page_images)

        return AskResult(
            evidence_result=evidence_result,
            candidates=tuple(candidates),
            page_images=tuple(page_images),
            map_reused=build_result.reused,
        )
