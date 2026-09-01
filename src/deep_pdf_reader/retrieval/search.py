from __future__ import annotations

from dataclasses import dataclass

from deep_pdf_reader.models import CandidatePage, DocumentMap, PageMapEntry
from deep_pdf_reader.retrieval.bm25 import BM25, tokenize


@dataclass(frozen=True, slots=True)
class _RankedPage:
    entry: PageMapEntry
    score: float
    reasons: tuple[str, ...]


class MapSearcher:
    """Section-first lexical retrieval over untrusted navigation metadata."""

    def search(
        self,
        document_map: DocumentMap,
        question: str,
        *,
        limit: int = 5,
        exclude_pages: frozenset[int] = frozenset(),
    ) -> tuple[CandidatePage, ...]:
        if not question.strip():
            raise ValueError("Question must not be empty")
        bounded_limit = max(3, min(8, limit))
        available_pages = [
            page for page in document_map.pages if page.page not in exclude_pages
        ]
        if not available_pages:
            return ()

        query_tokens = tokenize(question)
        section_scores = self._section_scores(document_map, question, query_tokens)
        page_corpus = [self._page_text(page) for page in available_pages]
        lexical_scores = BM25([tokenize(text) for text in page_corpus]).scores(
            query_tokens
        )
        ranked = [
            self._rank_page(
                entry=page,
                question=question,
                query_tokens=query_tokens,
                bm25_score=lexical_scores[index],
                section_score=section_scores.get(page.section_path, 0.0),
            )
            for index, page in enumerate(available_pages)
        ]
        ranked.sort(key=lambda item: (-item.score, item.entry.page))
        desired = min(bounded_limit, len(ranked))
        seed_count = max(1, desired - 2)
        selected: dict[int, _RankedPage] = {
            item.entry.page: item for item in ranked[:seed_count]
        }
        by_page = {item.entry.page: item for item in ranked}

        for seed in ranked[:seed_count]:
            if len(selected) >= desired:
                break
            self._expand_neighbors(seed, selected, by_page, desired)

        for item in ranked:
            if len(selected) >= desired:
                break
            selected.setdefault(item.entry.page, item)

        ordered = sorted(selected.values(), key=lambda item: (-item.score, item.entry.page))
        return tuple(
            CandidatePage(
                page=item.entry.page,
                section_path=item.entry.section_path,
                score=round(item.score, 4),
                reasons=item.reasons,
                summary=item.entry.summary,
            )
            for item in ordered
        )

    @staticmethod
    def _section_scores(
        document_map: DocumentMap,
        question: str,
        query_tokens: list[str],
    ) -> dict[tuple[str, ...], float]:
        if not document_map.sections:
            return {}
        section_texts = [" ".join(section.path) for section in document_map.sections]
        bm25_scores = BM25([tokenize(text) for text in section_texts]).scores(
            query_tokens
        )
        normalized_question = question.casefold()
        scores: dict[tuple[str, ...], float] = {}
        for section, text, bm25_score in zip(
            document_map.sections, section_texts, bm25_scores, strict=True
        ):
            normalized_section = text.casefold()
            overlap = len(set(query_tokens) & set(tokenize(text)))
            exact_bonus = (
                4.0
                if normalized_section
                and (
                    normalized_section in normalized_question
                    or normalized_question in normalized_section
                )
                else 0.0
            )
            scores[section.path] = bm25_score + overlap * 1.5 + exact_bonus
        return scores

    @staticmethod
    def _page_text(page: PageMapEntry) -> str:
        return " ".join(
            [
                " ".join(page.section_path),
                page.summary,
                " ".join(page.keywords),
                " ".join(page.entities),
            ]
        )

    @staticmethod
    def _rank_page(
        entry: PageMapEntry,
        question: str,
        query_tokens: list[str],
        bm25_score: float,
        section_score: float,
    ) -> _RankedPage:
        normalized_question = question.casefold()
        page_text = MapSearcher._page_text(entry).casefold()
        reasons: list[str] = []
        score = bm25_score
        if bm25_score > 0:
            reasons.append(f"BM25 lexical match {bm25_score:.2f}")

        if normalized_question in page_text:
            score += 6.0
            reasons.append("exact question phrase")

        keyword_matches = [
            keyword
            for keyword in entry.keywords
            if keyword.casefold() in normalized_question
            or normalized_question in keyword.casefold()
        ]
        if keyword_matches:
            score += min(4.0, len(keyword_matches) * 1.25)
            reasons.append("keyword match: " + ", ".join(keyword_matches[:3]))

        entity_matches = [
            entity
            for entity in entry.entities
            if entity.casefold() in normalized_question
            or normalized_question in entity.casefold()
        ]
        if entity_matches:
            score += min(6.0, len(entity_matches) * 2.0)
            reasons.append("entity match: " + ", ".join(entity_matches[:3]))

        query_overlap = set(query_tokens) & set(tokenize(page_text))
        if query_overlap:
            score += min(3.0, len(query_overlap) * 0.35)
            reasons.append(f"{len(query_overlap)} query terms overlap")

        if section_score > 0:
            boost = section_score * 1.4
            score += boost
            reasons.append(f"section/title boost {boost:.2f}")

        if not reasons:
            reasons.append("fallback candidate for bounded visual inspection")
        return _RankedPage(entry=entry, score=score, reasons=tuple(reasons))

    @staticmethod
    def _expand_neighbors(
        seed: _RankedPage,
        selected: dict[int, _RankedPage],
        by_page: dict[int, _RankedPage],
        desired: int,
    ) -> None:
        for page_number in (seed.entry.page - 1, seed.entry.page + 1):
            if len(selected) >= desired:
                return
            neighbor = by_page.get(page_number)
            if neighbor is None or page_number in selected:
                continue
            same_section = (
                bool(seed.entry.section_path)
                and seed.entry.section_path == neighbor.entry.section_path
            )
            table_continuation = (
                seed.entry.has_table or neighbor.entry.has_table
            ) and (
                same_section
                or not seed.entry.section_path
                or not neighbor.entry.section_path
            )
            if not (same_section or table_continuation):
                continue
            reason = (
                f"neighbor of page {seed.entry.page} for possible table continuation"
                if table_continuation
                else f"neighbor of page {seed.entry.page} in the same section"
            )
            selected[page_number] = _RankedPage(
                entry=neighbor.entry,
                score=max(neighbor.score, seed.score * 0.72),
                reasons=tuple([*neighbor.reasons, reason]),
            )
