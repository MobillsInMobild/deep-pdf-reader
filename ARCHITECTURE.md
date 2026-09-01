# Architecture

## Core invariant

The document map is a lossy navigation index. It can rank pages, but it cannot
substantiate an answer. Every important fact in a final answer must be returned
by a `PageInspector` after it has inspected images rendered from the original
PDF pages.

This creates an explicit trust boundary:

```text
untrusted navigation metadata          authoritative evidence path
parser -> map -> retrieval -> page IDs -> render original pages -> inspector
```

The ask workflow never copies numeric facts from a map summary into evidence.

## Package boundaries

- `parsers`: converts a PDF into page-level text, layout clues, and coarse
  visual flags behind `DocumentParser`.
- `mapping`: builds and serializes a navigation map. `MapBuilder` receives a
  `TextModel`; it does not know vendor APIs.
- `providers`: text-generation interfaces and implementations. A deterministic
  provider supports offline use and tests; an OpenAI-compatible adapter supports
  hosted or internal endpoints.
- `retrieval`: section-first lexical retrieval, BM25 scoring, explicit boosts,
  and neighboring-page expansion.
- `rendering`: renders only requested source pages and caches those PNGs.
- `inspection`: turns rendered source pages into structured evidence behind a
  vendor-neutral `PageInspector` interface.
- `workflow`: coordinates map reuse, retrieval, lazy rendering, optional second
  retrieval, inspection, and answer formatting.
- `cli`: argument parsing and dependency wiring only.

## Design decisions

### Standard-library domain models

The core schema uses typed dataclasses with explicit JSON conversion. This
keeps serialization stable and makes the business layer independent of a
validation framework. Provider responses are validated at their boundary.

### Content-aware document identity

The document ID is derived from the resolved path, size, modification time, and
a streaming SHA-256 content digest. The map stores the same fingerprint. An
unchanged PDF reuses its map; a changed PDF cannot silently reuse stale
navigation metadata.

### PyMuPDF as the only MVP parser and renderer

`PyMuPDFParser` extracts text blocks and image/drawing information page by page.
Parser selection is injected through `DocumentParser`, so a future
`MinerUParser` can be added without changing mapping or retrieval.

### Conservative deterministic mapping

Offline mapping derives short topic summaries, keywords, entities, heading
clues, and layout flags without inventing facts. Generated summaries suppress
standalone numeric tokens. A configured `TextModel` may improve navigation
metadata, but its output remains untrusted and never becomes answer evidence.

### Pure Python BM25

The MVP avoids services and database setup. A compact BM25 implementation ranks
sections first, then pages. Exact phrase, entity, section/title, and token
overlap boosts are recorded as human-readable reasons. Candidate results expand
to adjacent pages when section continuity or possible table continuation makes
that useful.

### Lazy, bounded visual verification

Retrieval normally selects 3-8 pages. Only those pages are rendered. The
inspector receives page-numbered image paths and a strict prompt covering table
headers, units, signs, parentheses, footnotes, and year-column alignment. It
must report insufficient evidence instead of guessing.

### Cache location

Artifacts default to `.deep-pdf-reader/<document-id>/` beside the input PDF.
This makes different files and versions isolated and keeps source trees free of
global implicit state. A CLI/config override can relocate the cache.

## Retrieval policy

1. Rank section names/paths for the question.
2. Rank pages using BM25 and transparent lexical boosts.
3. Prefer exact matches and entity-like terms.
4. Use map summaries only to select pages.
5. Expand neighbors for multi-page sections and possible table continuations.
6. Inspect 3-8 source pages by default.
7. If the inspector explicitly requests more evidence, perform one bounded
   second retrieval excluding pages already inspected.
8. Never treat any retrieval score as evidence.

## Deferred work

The MVP deliberately excludes embeddings, vector databases, Elasticsearch,
ColPali/ColQwen, web UI, multi-user/distributed execution, knowledge graphs,
RAGFlow, and a MinerU dependency. These can be added behind existing parser,
retrieval, and inspector boundaries after the single-PDF workflow is proven.
