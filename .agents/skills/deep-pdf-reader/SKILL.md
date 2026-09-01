---
name: deep-pdf-reader
description: Analyze long or visually structured PDFs (长篇 PDF、年报、财务报告、研究报告、合同、手册), including annual and financial reports, research reports, contracts, manuals, scanned documents, complex tables, charts, and diagrams, when exact page-level evidence matters. Use a lightweight document map only to navigate, then visually verify claims on rendered source pages. Do not use for unrelated work or tiny plain-text documents that normal reading can handle directly.
---

# Deep PDF Reader

Use the installed `deep-pdf-reader` CLI as the deterministic document tool
layer. Perform question interpretation, retrieval planning, visual inspection,
evidence sufficiency decisions, synthesis, and page citation yourself.

The governing rule is:

> Map tells us where to look. The original page tells us what is true.

## Choose the execution mode

Prefer Skill mode inside Codex:

```text
Codex -> build-map/search/render -> inspect PNG pages -> reason -> answer
```

Do not normally call `deep-pdf-reader ask` from this skill. That command invokes
the engine's `PageInspector` and remains available for standalone, non-Codex
use. Avoid a nested VLM call when you can inspect the rendered images directly.

## Follow this workflow

1. Identify the exact source PDF. Resolve the user-provided path or attachment
   and confirm it is the intended document. Never silently substitute another
   file. If multiple PDFs are plausible and context cannot disambiguate them,
   ask which one to use.

2. Check the engine and map. Run:

   ```bash
   deep-pdf-reader build-map "<pdf>"
   ```

   The command validates the content-aware cache and reports whether it built or
   reused the map. Reuse a valid map; do not force a rebuild for every question.
   If the executable is unavailable, follow the engine installation guidance in
   the repository README or report the missing prerequisite.

3. Translate the user's question into one or more targeted retrieval queries.
   Do not blindly reuse a long prompt when decomposition would improve recall.
   Run each useful query separately:

   ```bash
   deep-pdf-reader search "<pdf>" "<targeted query>"
   ```

   For causal, comparative, or multi-section questions, read
   [references/retrieval-policy.md](references/retrieval-policy.md) before
   selecting pages.

4. Treat search output as navigation metadata only. Consider section paths,
   exact keyword/entity matches, neighboring pages, table continuation, and
   related sections. Normally select 3-8 pages in total.

5. Render only selected original pages:

   ```bash
   deep-pdf-reader render "<pdf>" --pages 83,84,117
   ```

   Open the emitted PNG paths with the available image-view capability. Preserve
   the page number encoded in each filename. Never pre-render the entire PDF
   unless bounded map-guided navigation has genuinely failed and the broader
   scan is necessary for the user's request.

6. Inspect the page images directly. Before relying on financial figures,
   tables, charts, footnotes, dates, percentages, or layout relationships, read
   and apply [references/evidence-policy.md](references/evidence-policy.md).
   Map summaries, extracted keywords, entities, and retrieval scores are not
   evidence.

7. Decide whether the inspected pages actually support the requested
   conclusion. If a specific fact, causal link, unit, period, or note is missing,
   identify the gap, formulate a narrower related query, and perform one bounded
   second search/render/inspection pass. Inspect related sections when needed;
   do not invent a bridge between them. If the second pass is still inadequate,
   report the insufficiency instead of scanning the whole PDF by default.

8. Answer from verified source-page evidence. Include exact PDF page numbers for
   important claims. Clearly distinguish direct observations, inferences that
   combine multiple pages, confidence, and remaining uncertainty.

## Output expectations

Use a compact structure appropriate to the question. For evidence-heavy answers,
prefer:

```text
Answer:
...

Evidence:
- Page 83: directly observed fact and its context.
- Page 117: directly observed supporting fact.

Inference:
... (only when needed, with the supporting pages named)

Confidence / insufficient evidence:
...
```

Never cite an amount, date, percentage, sign, unit, table relationship, or other
important fact solely because it appeared in `map.json` or search output.
