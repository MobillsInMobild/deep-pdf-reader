from __future__ import annotations

import base64
import json
import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from deep_pdf_reader.models import EvidenceItem, EvidenceResult
from deep_pdf_reader.providers.openai_compatible import OpenAICompatibleClient


_PAGE_NUMBER = re.compile(r"page-(\d+)\.png$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class OpenAICompatiblePageInspector:
    base_url: str
    api_key: str
    model: str
    timeout: float = 60.0

    def inspect(self, question: str, page_images: list[Path]) -> EvidenceResult:
        if not page_images:
            return EvidenceResult(
                answer="No source pages were available for inspection.",
                confidence="low",
                insufficient_evidence=("No candidate page images were rendered.",),
            )

        page_numbers = [_page_number(path) for path in page_images]
        content: list[dict[str, Any]] = [
            {"type": "text", "text": self._prompt(question, page_numbers)}
        ]
        for page_number, image_path in zip(page_numbers, page_images, strict=True):
            mime_type = mimetypes.guess_type(image_path.name)[0] or "image/png"
            encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
            content.extend(
                [
                    {"type": "text", "text": f"Original PDF page {page_number}:"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{encoded}",
                            "detail": "high",
                        },
                    },
                ]
            )

        response = OpenAICompatibleClient(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout,
        ).chat_completion(
            {
                "model": self.model,
                "messages": [{"role": "user", "content": content}],
                "temperature": 0,
                "response_format": {"type": "json_object"},
            }
        )
        try:
            raw_content = str(response["choices"][0]["message"]["content"])
            parsed = json.loads(_strip_json_fence(raw_content))
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError("Malformed multimodal inspection response") from exc
        return self._to_result(parsed, frozenset(page_numbers))

    @staticmethod
    def _prompt(question: str, page_numbers: list[int]) -> str:
        return f"""Answer the question using only the attached images of original PDF pages.

The original page images are the authoritative evidence. Navigation maps,
retrieval scores, summaries, and model memory are not evidence. Inspect the
page visually. For every important amount, date, percentage, table relationship,
or unit, check the table header, displayed unit, minus sign, parentheses,
footnotes, and which year/period column the value belongs to. Do not infer a
value from an adjacent column. Cite only attached pages: {page_numbers}.

If the pages do not establish the answer, say so explicitly and set
needs_more_evidence accordingly. Never guess.

Question: {question}

Return one JSON object with this schema:
{{
  "answer": "concise answer or explicit insufficiency",
  "evidence": [{{"page": 1, "detail": "what the original page establishes"}}],
  "confidence": "high|medium|low",
  "insufficient_evidence": ["missing fact or ambiguity"],
  "needs_more_evidence": false,
  "suggested_queries": ["bounded follow-up navigation query"]
}}
"""

    @staticmethod
    def _to_result(value: dict[str, Any], allowed_pages: frozenset[int]) -> EvidenceResult:
        evidence: list[EvidenceItem] = []
        for raw_item in value.get("evidence", []):
            page = int(raw_item["page"])
            if page not in allowed_pages:
                raise RuntimeError(
                    f"Inspector cited page {page}, which was not supplied for inspection"
                )
            evidence.append(EvidenceItem(page=page, detail=str(raw_item["detail"])))
        confidence = str(value.get("confidence", "low")).casefold()
        if confidence not in {"high", "medium", "low"}:
            confidence = "low"
        return EvidenceResult(
            answer=str(value.get("answer", "Evidence inspection returned no answer.")),
            evidence=tuple(evidence),
            confidence=confidence,
            insufficient_evidence=tuple(
                str(item) for item in value.get("insufficient_evidence", [])
            ),
            needs_more_evidence=bool(value.get("needs_more_evidence", False)),
            suggested_queries=tuple(
                str(item) for item in value.get("suggested_queries", [])
            ),
        )


def _page_number(path: Path) -> int:
    match = _PAGE_NUMBER.search(path.name)
    if not match:
        raise ValueError(f"Rendered page filename does not encode a page number: {path}")
    return int(match.group(1))


def _strip_json_fence(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped
