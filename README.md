# deep-pdf-reader

[English](README.md) | [简体中文](README_CN.md)

`deep-pdf-reader` is a small, testable toolkit for answering questions about a
single PDF without sending the whole document to a vision model.

Its governing rule is:

> Map tells us where to look. The original page tells us what is true.

The MVP workflow is:

```text
PDF -> page extraction -> document map -> cheap search -> candidate pages
    -> lazy page rendering -> visual evidence inspection -> cited answer
```

The document map contains navigation-oriented summaries, keywords, entities,
section paths, and coarse layout flags. It is not an authoritative facts
database. Amounts, dates, percentages, units, table relationships, and other
important claims in an answer must come from inspection of the rendered source
pages.

## Install

Use Python 3.11 or newer:

```bash
python -m venv .venv
# Windows: .venv\Scripts\python -m pip install -e ".[dev]"
# macOS/Linux: .venv/bin/python -m pip install -e ".[dev]"
```

Only PyMuPDF is required at runtime. `pytest` and `reportlab` are development
dependencies used to generate and exercise the offline PDF fixture.

## Commands

```bash
python -m deep_pdf_reader build-map report.pdf
python -m deep_pdf_reader search report.pdf "Why did operating cash flow decline?"
python -m deep_pdf_reader render report.pdf --pages 83,84,117
python -m deep_pdf_reader ask report.pdf "Why did operating cash flow decline?"
```

Maps and lazily rendered pages are stored below
`.deep-pdf-reader/<document-id>/` next to the source PDF by default. A map is
reused when its path, size, modification time, and SHA-256 fingerprint still
match the PDF. Override the cache location with `--cache-dir` before the
subcommand or with `DEEP_PDF_READER_CACHE_DIR`.

`search` prints ranked pages, section paths, scores, and transparent reasons.
Scores and summaries are navigation hints only. `render` creates PNGs only for
the requested 1-based page numbers.

`ask` searches 3-8 pages, renders only those pages, and supplies the page images
to a `PageInspector`. Its output has four explicit sections:

```text
Answer:
...

Evidence:
- Page 2: ...

Confidence:
...

Insufficient evidence:
...
```

Without a configured vision model, `ask` uses the safe mock inspector and
returns an explicit insufficient-evidence result. It does not promote map text
into an answer.

## OpenAI-compatible providers

Both hosted OpenAI-compatible APIs and internal endpoints such as GLM gateways
can be configured without changing business logic:

```bash
set DEEP_PDF_READER_BASE_URL=https://example.internal/v1
set DEEP_PDF_READER_API_KEY=your-key
set DEEP_PDF_READER_TEXT_MODEL=your-text-model
set DEEP_PDF_READER_VISION_MODEL=your-vision-model
python -m deep_pdf_reader ask report.pdf "Why did cash flow decline?"
```

On macOS/Linux, use `export` instead of `set`. Optional settings are:

- `DEEP_PDF_READER_CACHE_DIR`
- `DEEP_PDF_READER_CANDIDATE_PAGES` (clamped to 3-8)
- `DEEP_PDF_READER_REQUEST_TIMEOUT`

The text model only generates navigation metadata. The vision model receives
the rendered candidate pages and is required to check table headers, units,
signs, parentheses, footnotes, and year/period columns. An endpoint may use the
text adapter, the vision adapter, both, or neither.

## Document map

`map.json` is human-readable and contains document metadata, flat section
ranges, and page entries such as:

```json
{
  "page": 12,
  "section_path": ["MD&A", "Liquidity"],
  "summary": "Contains discussion of operating cash flow and comparisons.",
  "keywords": ["operating", "cash", "flow"],
  "entities": ["Operating Cash Flow"],
  "has_table": true,
  "has_chart": false,
  "has_image": false
}
```

Numeric details are suppressed from generated summaries. Even so, every map
field remains untrusted navigation metadata.

## Retrieval behavior

The lexical retriever ranks section paths first and then pages. It combines
BM25 with exact phrase, keyword, entity, query-token, and section/title boosts.
It expands neighboring pages for a continuing section or possible cross-page
table, while refusing to treat the score as evidence. If a visual inspector
explicitly reports missing evidence, `ask` may perform one bounded second
retrieval, never exceeding eight inspected pages.

## Development

The project targets Python 3.11+ and uses a `src/` package layout.

```bash
python -m pip install -e ".[dev]"
pytest
python -m deep_pdf_reader --help
```

The suite creates a four-page PDF locally. It covers page extraction, two-level
section inference, table detection, map serialization/reuse, keyword retrieval,
section boosting, neighbor expansion, lazy PNG rendering, mock inspection, and
the end-to-end ask workflow.

## Using as a Codex Skill

This repository includes a current-format Codex Skill at:

```text
$REPO_ROOT/.agents/skills/deep-pdf-reader/
```

Codex scans `.agents/skills` from the current working directory up to the
repository root. Launch Codex anywhere inside this repository to make the Skill
available. The current official discovery and authoring rules are documented in
[OpenAI's Build skills guide](https://developers.openai.com/codex/skills/).

Invoke it explicitly in Codex CLI or the IDE extension with:

```text
$deep-pdf-reader Analyze this annual report and explain the cash-flow decline.
```

`/skills` can be used to inspect available Skills. Implicit invocation is also
enabled: Codex can select the Skill for long or visually structured PDF tasks,
financial/annual/research reports, contracts, manuals, complex tables/charts,
or questions requiring exact page evidence. It should not trigger for unrelated
coding work or tiny plain-text documents that can be read normally.

### Install the engine used by the Skill

The Skill orchestrates the existing CLI; it does not copy the Python engine.
Install the repository package into the environment from which Codex runs:

```bash
python -m pip install -e "$REPO_ROOT"
deep-pdf-reader --help
```

If a virtual environment is used, launch Codex with that environment activated
so the `deep-pdf-reader` console command is on `PATH`.

### Make the Skill personal/global without copying it

Codex also scans:

```text
$HOME/.agents/skills/deep-pdf-reader/
```

Symlink the repository Skill into that location so source and Skill instructions
remain single-sourced. On macOS/Linux:

```bash
mkdir -p "$HOME/.agents/skills"
ln -s "$REPO_ROOT/.agents/skills/deep-pdf-reader" \
  "$HOME/.agents/skills/deep-pdf-reader"
```

On Windows PowerShell, from the repository root:

```powershell
$RepoRoot = (Resolve-Path ".").Path
New-Item -ItemType Directory -Force "$HOME\.agents\skills" | Out-Null
New-Item -ItemType SymbolicLink `
  -Path "$HOME\.agents\skills\deep-pdf-reader" `
  -Target "$RepoRoot\.agents\skills\deep-pdf-reader"
```

Codex follows symlinked Skill folders. If a newly linked Skill does not appear,
restart Codex.

### Skill mode vs standalone mode

```text
Standalone mode
User -> deep-pdf-reader ask -> internal PageInspector

Codex Skill mode (preferred inside Codex)
User -> Codex -> SKILL.md -> build-map/search/render
     -> Codex visual inspection/reasoning -> page-cited answer
```

Standalone `ask` remains supported for non-Codex environments. Skill mode uses
Codex itself for query planning, iterative navigation, visual evidence review,
and synthesis, avoiding an unnecessary nested VLM call.

## MVP limitations

- Single local PDF per command; no multi-document corpus or cross-document QA.
- Text PDFs work best. Scanned/image-only PDFs have visual flags but no OCR in
  the deterministic map builder.
- Heading and table detection are conservative heuristics, not a full layout
  reconstruction engine.
- Retrieval is lexical; there are no embeddings or vector database.
- The OpenAI-compatible adapters use Chat Completions-style JSON responses;
  endpoint-specific authentication or payload extensions may need a small
  adapter.
- No Elasticsearch, ColPali/ColQwen, web UI, multi-user state, distributed
  tasks, knowledge graph, RAGFlow, or required MinerU installation is included.
