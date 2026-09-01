# Repository instructions for Codex agents

These instructions apply to the entire repository.

## Non-negotiable business principles

1. **Map tells us where to look. The original page tells us what is true.**
2. Treat map summaries, keywords, entities, section inference, retrieval scores,
   and model-generated navigation metadata as untrusted hints.
3. Important amounts, dates, percentages, units, signs, table relationships,
   and footnotes in answers must come from direct Codex visual inspection or
   `PageInspector` output produced from rendered original PDF pages.
4. Render lazily. Do not pre-render or send the whole PDF to a visual model.
5. Default to a bounded 3-8 candidate pages and allow only explicit, bounded
   secondary retrieval when evidence is insufficient.
6. Never hard-code an AI vendor in parser, mapping, retrieval, rendering, or
   workflow business logic. Use the provider protocols and dependency injection.

## Engineering constraints

- Target Python 3.11+ and keep complete type hints on public APIs.
- Prefer small modules, dataclasses, `pathlib`, explicit dependencies, and pure
  functions where practical.
- Keep the CLI thin; orchestration belongs in the workflow layer.
- Preserve backward compatibility of `map.json`, or increment its schema
  version and add migration/validation tests.
- Do not add Elasticsearch, a vector database, ColPali, ColQwen, RAGFlow,
  MinerU as a required dependency, a web UI, distributed jobs, or multi-user
  state during the MVP.
- Tests must be offline and deterministic. Generate PDF fixtures locally; do not
  fetch test data from the network.
- Do not commit API keys, PDFs containing private data, rendered cache output,
  `.deep-pdf-reader/`, or test temp directories.

## Required validation

Run from the repository root:

```bash
pytest
python -m deep_pdf_reader --help
```

For CLI or workflow changes, also run the applicable offline smoke path using a
generated test PDF. New behavior requires focused tests. At minimum preserve
coverage for extraction, map serialization/reuse, keyword retrieval, section
boosting, neighboring-page expansion, rendering, mock inspection, and the
end-to-end ask workflow.

## Provider changes

- Configuration comes from environment variables and/or an explicit config
  object, never import-time global mutable state.
- OpenAI-compatible adapters must support configurable `base_url`, `api_key`,
  and `model`.
- Inspection prompts must state that source page images are authoritative and
  explicitly require checking headers, units, minus signs, parentheses,
  footnotes, and year-column alignment.
- An inspector must be able to return structured `insufficient_evidence` without
  fabricating an answer.

## Codex Skill changes

- Keep repository-local skills under `.agents/skills/`; do not introduce the
  legacy `.codex/skills` layout.
- Treat `src/deep_pdf_reader` as the deterministic tool layer. Do not duplicate
  engine logic in Skill scripts.
- In Codex Skill mode, prefer `build-map`, `search`, and `render`, followed by
  direct inspection of the rendered page images. Preserve standalone `ask` but
  do not make it the normal Skill orchestration path.
- Validate changed Skills with the bundled `skill-creator` validator and keep
  `agents/openai.yaml` consistent with `SKILL.md`.

## Documentation

Update `README.md` for user-visible commands or configuration. Record material
trust-boundary, cache, retrieval, or provider decisions in `ARCHITECTURE.md`.


# Git Workflow

Git history is part of the project deliverable.

Maintain the repository continuously while developing.

## General rules

Before starting work:

1. Run `git status`.
2. Inspect recent history with `git log --oneline -10`.
3. Understand the current branch and existing uncommitted changes.
4. Never discard user changes.

If the repository has not yet been initialized, initialize Git before substantial development begins.

## Commit policy

Create commits continuously during implementation.

Do not wait until the entire task is finished before committing.

Commit after each coherent, independently understandable milestone.

Examples of appropriate milestones:

* project scaffolding;
* parser implementation;
* map schema;
* map builder;
* retrieval implementation;
* page renderer;
* model/provider adapter;
* page inspector;
* ask workflow;
* evaluation framework;
* documentation.

A commit should ideally:

* perform one conceptual change;
* leave the repository in a working state;
* pass the relevant tests;
* be understandable without reading later commits.

Do not create commits for trivial intermediate edits such as:

* typo fixes made during an unfinished feature;
* temporary debugging output;
* half-written implementations;
* formatting changes incidental to an unfinished feature.

Combine those into the related logical commit.

## Before every commit

Before committing:

1. Review `git diff`.
2. Review `git status`.
3. Remove accidental debug code and temporary files.
4. Run the tests relevant to the changed code.
5. Run formatting/linting checks if configured.
6. Ensure secrets, credentials, local caches, generated pages, and environment files are not staged.

If tests fail because of the current change, fix them before committing.

Do not knowingly commit a broken intermediate state unless there is a compelling reason documented in the commit message.

## Commit messages

Use Conventional Commit style.

Preferred prefixes:

* `feat:` new functionality
* `fix:` bug fix
* `refactor:` structural change without behavior change
* `test:` tests or evaluation improvements
* `docs:` documentation
* `chore:` tooling/configuration
* `perf:` performance improvement

Examples:

`feat: add PyMuPDF document parser`

`feat: implement hierarchical document map`

`feat: add BM25 page retrieval`

`fix: preserve page numbers during map serialization`

`test: add page recall evaluation`

Keep commit messages concise and specific.

Avoid messages such as:

* `update`
* `changes`
* `work`
* `fix stuff`
* `wip`

## Existing history

Do not rewrite existing history.

Unless explicitly instructed by the user:

* do not amend existing commits;
* do not rebase;
* do not squash existing commits;
* do not reset shared history;
* do not use `git push --force`;
* do not delete branches;
* do not alter existing tags.

Prefer adding a new corrective commit.

## Branches

Work on the branch provided by the user or environment.

Do not create, rename, switch, merge, or delete branches unless the task specifically requires it.

If Codex is operating inside an isolated worktree, preserve that worktree model.

## Remote operations

Local commits are encouraged and should happen automatically.

Do NOT automatically:

* `git push`;
* create a pull request;
* merge a pull request;
* modify remote branches;
* create releases or tags.

Remote operations require an explicit user request.

## User changes

Never overwrite or discard unrelated user modifications.

If unrelated uncommitted changes already exist:

* preserve them;
* avoid staging them;
* stage only files belonging to the current logical change when practical.

Do not use destructive commands such as:

`git reset --hard`

`git clean -fd`

`git checkout -- <user-file>`

unless the user explicitly requests the destructive operation.

## Generated files

Do not commit runtime-generated artifacts unless they are intentional test fixtures.

For this project, local generated data such as the following should normally be ignored:

`.deep-pdf-reader/`

Rendered PDF pages

Runtime caches

Local model outputs

Temporary evaluation outputs

Local databases created during experiments

Environment files containing credentials

Add appropriate entries to `.gitignore`.

## Checkpoints

For long tasks, use Git commits as checkpoints.

Before undertaking a risky refactor or substantial architectural change, make sure the current working implementation has already been committed.

This should make it possible to recover easily if the experiment fails.

## End-of-task requirements

Before considering a task complete:

1. Run the complete relevant test suite.
2. Run `git status`.
3. Review the final diff.
4. Commit all intended source changes.
5. Confirm there are no unintended tracked changes.
6. Leave the worktree clean unless there are deliberately preserved user changes.
7. Show the recent commit history with:

   `git log --oneline --decorate -10`

In the final report, summarize:

* commits created;
* major changes in each commit;
* tests executed;
* current repository status.

Git history should tell the story of how the implementation evolved.
