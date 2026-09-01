# Retrieval policy

Use this policy for causal, comparative, multi-hop, or cross-section PDF
questions, and whenever the first candidates do not establish the answer.

## Form queries from the information need

Prefer short, section-oriented queries over one overloaded prompt. Decompose the
question into evidence lanes when useful:

- the primary metric, clause, event, component, or technical term;
- management explanation or narrative discussion;
- the primary statement, schedule, specification, or operative clause;
- likely drivers, definitions, notes, exceptions, or appendices;
- relevant entity names and period terms.

Example for a cash-flow decline:

```text
search "经营活动现金流"
search "经营现金流 下降 原因"
search "应收账款"
search "存货 营运资本"
```

Use only the queries needed for the actual question. Do not mechanically run
every possible synonym.

## Rank sections before pages

Interpret section paths before individual scores. Prefer candidates supported
by exact keywords/entities and a relevant section title. Then consider:

- adjacent pages in the same section;
- pages before or after a table that may continue;
- the primary statement plus explanatory notes or management discussion;
- definitions or appendices needed to interpret a term;
- pages returned by different targeted queries that address distinct evidence
  lanes.

A high score is not proof. A lower-ranked page can be essential when it contains
the definition, footnote, or causal explanation.

## Keep retrieval bounded

Normally inspect 3-8 unique pages total. Deduplicate pages returned by multiple
queries. Render only selected pages and their justified neighbors.

Use this loop:

```text
search -> select -> render -> inspect -> sufficiency decision
                                      |
                                      +-- insufficient -> refine query
                                                          -> second search
                                                          -> render new pages
                                                          -> inspect again
```

The second pass must target a named evidence gap and exclude pages already
inspected unless a higher-detail reread is required. Stop when the evidence is
sufficient or when a bounded second pass fails. Do not turn failure into an
unbounded whole-document scan.

## Common evidence combinations

- Financial report: primary statement + MD&A + relevant note.
- Contract: operative clause + definition + exception/schedule.
- Research report: result figure/table + methods/definition + limitation.
- Manual: procedure + warning + diagram or prerequisite section.

Combine pages only after directly inspecting each rendered image. State when
the final conclusion is an inference across sections rather than wording found
verbatim on one page.
