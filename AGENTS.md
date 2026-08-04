# Agent Working Agreement

This repository is a learning system, not a notebook dump. The learner owns the
football question, assumptions, interpretation, and final claims. The agent
owns implementation quality, reproducibility, validation, and clear
explanation.

## Session Startup

Before lesson work:

1. Read `course/state.yaml`.
2. Read the active lesson's `brief.md` and `handoff.md`.
3. Read the relevant parts of `course/syllabus.md`, `docs/methodology.md`, and
   `docs/data-guide.md`.

Then inspect `git status`, `git log --oneline -5`, and any post-commit diff.
Summarize the current lesson, latest recoverable commit, uncommitted work, and
next action before resuming. Never discard or auto-commit existing changes.

## Scope

- Work on one bounded lesson or infrastructure task at a time.
- Do not silently broaden the research question.
- Do not infer tactical causes from event data alone.
- Do not commit files under `data/external/` or `data/processed/`.
- Do not add a heavy dependency until a current lesson needs it.
- Core lessons must run on local CPU.
- Preserve user-authored findings and unrelated working-tree changes.

## Lesson Contract

Before coding, ensure the active lesson has a concrete question, unit of
analysis, comparison baseline, outcome, required fields, assumptions, and
acceptance criteria in `brief.md`.

During implementation:

- Keep reusable loading, validation, metrics, and plotting logic under `src/`.
- Use notebooks for orchestration, inspection, and narrative.
- Prefer explicit metric definitions over opaque helper calls.
- Add tests proportional to the analytical risk.
- Make randomness deterministic.
- Record the upstream open-data commit in completed findings.

When a lesson enters review:

- Restart and execute notebooks top-to-bottom.
- Run the checks required by the lesson and changed implementation.
- Update `findings.md`, `checks.md`, `exercises.md`, and `handoff.md`.
- Update `course/state.yaml` only when global navigation changes.
- Explain the outputs and limitations to the learner.

## Data Selection

Use `$select-match-data` when locating competitions, seasons, teams, managers,
or matches and when fetching open-data files. Resolve names to stable IDs,
report catalog coverage, and confirm ambiguous or incomplete scopes before
analysis. Do not bypass the catalog with ad hoc source parsing unless
diagnosing the catalog itself.

## Book Reference

Use `$book-reference` whenever the learner asks to compare with *Soccer Analytics
with Machine Learning*, its chapters, notebooks, code, or companion repository.
Query the pinned local checkout through `book-ref`; do not browse or pull upstream
when the local reference is ready. Report the source commit, relative path, and
notebook cell or text line used for a material comparison.

## Turn Completion And Checkpoints

Use `$course-turn-checkpoint` after any turn that modifies the repository. The
Skill owns the decision to run a focused check, update the lesson handoff, leave
work uncommitted, or create a local commit. Never push merely because a turn
ended.

## Explanation Contract

For every material output, explain:

1. What question it answers.
2. What rows, events, or samples went into it.
3. How it was calculated.
4. How to read it in football terms.
5. What it does not establish.
6. What check would make the conclusion more credible.

Label claims using the evidence ladder in `docs/methodology.md`: data fact,
metric result, football interpretation, or unverified hypothesis.

## Validation

Choose checks from the current diff, lesson acceptance criteria, and analytical
risk. Execute a changed lesson notebook from a clean kernel when it enters
review. Never claim a lesson is complete from a successful cell run in an
existing interactive kernel.

Before an explicit push or PR update, inspect the full branch diff, run all
relevant repository and lesson checks, and repair failures in a bounded loop.
CI is the final branch-wide gate.

## Handoff

The handoff frontmatter is the latest resumable snapshot. Its body must state:

- completed learning work and the current boundary;
- decisions and definitions introduced;
- relevant checks, results, and checks not yet run;
- unresolved questions or limitations.

Do not leave essential context only in the chat transcript.

After the learner accepts completion, checkpoint `completed`, update global
navigation, push the lesson branch, open one lesson PR, and observe CI. Squash
merge only after explicit merge confirmation.
