from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable, Sequence


_ASCII_TERM = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
_CJK_RUN = re.compile(r"[\u3400-\u9fff]+")


def tokenize(value: str) -> list[str]:
    """Tokenize English-like text and add CJK characters/bigrams."""

    tokens = [match.group(0).casefold() for match in _ASCII_TERM.finditer(value)]
    for match in _CJK_RUN.finditer(value):
        run = match.group(0)
        tokens.extend(run)
        tokens.extend(run[index : index + 2] for index in range(len(run) - 1))
    return tokens


class BM25:
    def __init__(
        self,
        documents: Sequence[Sequence[str]],
        *,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self._documents = [tuple(document) for document in documents]
        self._frequencies = [Counter(document) for document in self._documents]
        self._k1 = k1
        self._b = b
        self._average_length = (
            sum(len(document) for document in self._documents) / len(self._documents)
            if self._documents
            else 0.0
        )
        document_frequency: Counter[str] = Counter()
        for document in self._documents:
            document_frequency.update(set(document))
        total_documents = len(self._documents)
        self._idf = {
            term: math.log(
                1.0 + (total_documents - frequency + 0.5) / (frequency + 0.5)
            )
            for term, frequency in document_frequency.items()
        }

    def scores(self, query_tokens: Iterable[str]) -> list[float]:
        query = tuple(dict.fromkeys(query_tokens))
        return [
            self._score_document(index, query)
            for index in range(len(self._documents))
        ]

    def _score_document(self, index: int, query: tuple[str, ...]) -> float:
        frequencies = self._frequencies[index]
        document_length = len(self._documents[index])
        normalization = (
            1.0 - self._b
            + self._b * document_length / max(self._average_length, 1.0)
        )
        score = 0.0
        for term in query:
            frequency = frequencies.get(term, 0)
            if not frequency:
                continue
            score += self._idf.get(term, 0.0) * (
                frequency * (self._k1 + 1.0)
                / (frequency + self._k1 * normalization)
            )
        return score
