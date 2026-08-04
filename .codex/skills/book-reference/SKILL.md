---
name: book-reference
description: Query and compare against the pinned Soccer Analytics with Machine Learning companion repository through the local book-ref interface. Use when the learner asks what the original book or repository does, requests chapter or notebook code, wants an implementation aligned with the book, or needs an exact upstream path, cell, snippet, or version citation.
---

# Book Reference

Use the committed source manifest and local clone as the authoritative comparison surface.
Do not browse GitHub or pull upstream merely because the learner asks about the book.

## Query the pinned source

1. Read `references/soccer-analytics-ml.md` when the question may already have a curated
   chapter or notebook entry.
2. Verify the checkout before every comparison:

   ```bash
   uv run book-ref status
   ```

3. If status is `missing`, initialize once with `uv run book-ref sync`. If it is
   `dirty` or `commit_mismatch`, stop and report the state; do not discard changes or
   silently update the pin.
4. Search locally, narrowing by chapter or cell type when useful:

   ```bash
   uv run book-ref search "<query>" --chapter <number>
   uv run book-ref search "<query>" --cell-type code
   ```

5. Inspect only the relevant file or cell returned by search:

   ```bash
   uv run book-ref show <relative-path> --cell <zero-based-index>
   ```

## Report the comparison

- Cite the manifest commit, upstream-relative path, and notebook cell or text line.
- Separate what the book does from what this project adopts, changes, or rejects.
- Explain material changes in metric definition, sample, missing-data handling, plotting
  scale, or evidence boundary.
- Treat the curated index as navigation, not proof that no other relevant source exists.
- Add a repeatedly useful confirmed path to the index in the same repository change.

## Preserve reproducibility

- Never run `git pull` in the reference checkout.
- Never change `references/sources.toml` without an explicit version-update task.
- Keep the cloned repository under `references/external/`; never commit its contents.
- For a version update, review upstream changes, update the index, rerun affected lessons,
  and deliver the pin change through a dedicated PR.
