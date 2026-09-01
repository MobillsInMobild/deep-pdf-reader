from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from deep_pdf_reader.config import Settings
from deep_pdf_reader.models import AskResult, CandidatePage
from deep_pdf_reader.workflow import DeepPdfReader


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deep-pdf-reader",
        description=(
            "Search a lightweight PDF map, then verify facts on rendered source pages."
        ),
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        help="Override the default .deep-pdf-reader cache directory.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_map = subparsers.add_parser("build-map", help="Build or reuse a document map.")
    build_map.add_argument("pdf", type=Path)
    build_map.add_argument("--force", action="store_true", help="Rebuild an existing map.")

    search = subparsers.add_parser("search", help="Search navigation metadata.")
    search.add_argument("pdf", type=Path)
    search.add_argument("question")
    search.add_argument("--limit", type=_candidate_limit, default=None)

    render = subparsers.add_parser("render", help="Lazily render selected source pages.")
    render.add_argument("pdf", type=Path)
    render.add_argument("--pages", required=True, type=_page_list)

    ask = subparsers.add_parser(
        "ask", help="Search, render source pages, and inspect visual evidence."
    )
    ask.add_argument("pdf", type=Path)
    ask.add_argument("question")
    ask.add_argument("--limit", type=_candidate_limit, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    settings = Settings.from_env()
    if arguments.cache_dir is not None:
        settings = Settings(
            cache_dir=arguments.cache_dir,
            base_url=settings.base_url,
            api_key=settings.api_key,
            text_model=settings.text_model,
            vision_model=settings.vision_model,
            request_timeout=settings.request_timeout,
            candidate_pages=settings.candidate_pages,
        )
    try:
        reader = DeepPdfReader.from_settings(settings)
        if arguments.command == "build-map":
            result = reader.build_map(arguments.pdf, force=arguments.force)
            status = "reused" if result.reused else "built"
            print(f"Document map {status}: {result.map_path}")
            print(f"Pages: {result.document_map.document.page_count}")
            return 0
        if arguments.command == "search":
            result = reader.search(
                arguments.pdf, arguments.question, limit=arguments.limit
            )
            _print_candidates(result.candidates)
            return 0
        if arguments.command == "render":
            paths = reader.render(arguments.pdf, arguments.pages)
            print("Rendered pages:")
            for path in paths:
                print(f"- {path}")
            return 0
        if arguments.command == "ask":
            result = reader.ask(arguments.pdf, arguments.question, limit=arguments.limit)
            _print_ask_result(result)
            return 0
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    parser.error(f"Unknown command: {arguments.command}")
    return 2


def _print_candidates(candidates: tuple[CandidatePage, ...]) -> None:
    print("Candidate pages:\n")
    if not candidates:
        print("No candidate pages found.")
        return
    for index, candidate in enumerate(candidates, start=1):
        section = " > ".join(candidate.section_path) or "Document"
        print(f"{index}. Page {candidate.page}")
        print(f"   Section: {section}")
        print(f"   Score: {candidate.score:.4f}")
        print(f"   Reason: {'; '.join(candidate.reasons)}")
        print()


def _print_ask_result(result: AskResult) -> None:
    evidence = result.evidence_result
    print("Answer:")
    print(evidence.answer)
    print("\nEvidence:")
    if evidence.evidence:
        for item in evidence.evidence:
            print(f"- Page {item.page}: {item.detail}")
    else:
        print("- None established from the inspected source pages.")
    print("\nConfidence:")
    print(evidence.confidence)
    print("\nInsufficient evidence:")
    if evidence.insufficient_evidence:
        for item in evidence.insufficient_evidence:
            print(f"- {item}")
    else:
        print("- None reported.")


def _page_list(value: str) -> list[int]:
    try:
        pages = [int(item.strip()) for item in value.split(",") if item.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Pages must be comma-separated integers") from exc
    if not pages or any(page < 1 for page in pages):
        raise argparse.ArgumentTypeError("Pages must contain positive integers")
    return list(dict.fromkeys(pages))


def _candidate_limit(value: str) -> int:
    try:
        limit = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Candidate limit must be an integer") from exc
    if not 3 <= limit <= 8:
        raise argparse.ArgumentTypeError("Candidate limit must be between 3 and 8")
    return limit


if __name__ == "__main__":
    raise SystemExit(main())
