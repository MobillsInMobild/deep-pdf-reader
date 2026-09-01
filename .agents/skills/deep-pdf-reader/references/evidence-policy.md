# Evidence policy

Apply this policy whenever the answer depends on page content, especially
financial figures, dates, percentages, contracts, tables, charts, diagrams, or
footnotes.

## Authority boundary

The rendered image of the original PDF page is authoritative. The following are
navigation hints, never final evidence:

- `map.json` summaries, keywords, entities, and inferred section paths;
- BM25 scores, boosts, ranking order, and retrieval reasons;
- model memory or assumptions about what a report normally contains;
- a value seen only in extracted navigation text.

Never cite a number or relationship solely from the map. If a candidate page
cannot be rendered or read clearly, mark the evidence unavailable or
insufficient.

## Visual verification checklist

Inspect the full relevant region and verify every applicable item:

- row label and any indentation or subtotal relationship;
- column header and the exact year, quarter, date, or comparison period;
- displayed unit, currency, scale, and whether the unit applies to the whole
  table, chart, column, or footnote;
- minus signs, parentheses, percentage signs, decimal places, and blanks;
- footnote markers, superscripts, legends, axes, and source notes;
- whether a table, sentence, chart, or note continues on another page;
- whether consolidated, segment, adjusted, non-GAAP, gross, or net measures are
  being compared like-for-like.

For scanned or visually complex pages, zoom or inspect at original detail when
available. If text or a sign remains illegible, do not guess.

## Evidence ledger

Keep a small internal ledger while inspecting:

```text
Page | Direct observation | Claim supported | Caveat
```

Use only direct observations in the evidence list. When multiple observed facts
support a conclusion that no single page states, label the conclusion as an
inference and cite every supporting page.

## Sufficiency test

Before answering, ask:

> Do the inspected source pages actually support the requested conclusion?

Evidence is insufficient when the relevant unit, period, comparator, causal
statement, definition, table continuation, or footnote is missing or ambiguous.
Use one bounded follow-up retrieval pass to seek the missing item. If it remains
missing, state exactly what could not be established.

## Citation behavior

- Cite the exact 1-based PDF page number shown by the rendered filename.
- Attach the page number to the claim it supports, not only in a trailing list.
- Distinguish printed page labels from PDF page indices if the document displays
  both; the engine and PNG filename use the PDF page index.
- Never cite an unrendered page as verified evidence.
