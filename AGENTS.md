# Agent Working Agreement

This repository is a learning system, not a notebook dump. The learner owns the
football question, assumptions, interpretation, and final claims. The agent
owns implementation quality, reproducibility, validation, and clear
explanation.

## Session Startup

Before changing anything:

1. `README.md`
2. `course/syllabus.md`
3. `course/state.yaml`
4. The active lesson's `brief.md` and `handoff.md`
5. `docs/methodology.md`
6. `docs/agent-workflow.md`

Then inspect `git status`, `git log --oneline -5`, and any post-commit diff.
Present the current lesson, latest recoverable commit, worktree state, and next
action before continuing. Never discard or auto-commit post-checkpoint changes.
Treat tracked course state as authoritative over prior chat summaries.

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

Before finishing:

- Restart and execute notebooks top-to-bottom.
- Run the validation commands required by the lesson and repository.
- Update `findings.md`, `checks.md`, `exercises.md`, and `handoff.md`.
- Update `course/state.yaml` only when global navigation changes.

## Turn Completion And Checkpoints

Use `$course-turn-checkpoint` whenever a turn modified the repository. Start
with `git status --short`; if clean, finish without extra work. If dirty,
inspect the diff and reason separately about:

1. whether the current change is coherent and ready to commit;
2. whether a focused check is needed to make that decision;
3. whether learning progress advanced enough to update the active handoff.

Do not run generic tests merely because files changed. Do not update the lesson
handoff for technical cleanup alone. Leave unfinished work uncommitted with a
clear explanation.

When a coherent learning unit and its handoff snapshot are ready, commit
locally as `checkpoint(<lesson-id>): CP-NNN <step>`. A pause or block may also
be checkpointed if the handoff states what remains and which relevant checks
were not run or failed. Use a normal commit for coherent non-learning work.
Never push merely because a turn ended.

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

Choose checks from the current diff and analytical risk. Prose and course-state
changes usually need inspection, not a test suite. Deterministic reusable code
gets focused tests. Check notebook sections while building them; execute a
changed lesson notebook from a clean kernel when it enters review. Never claim
a lesson is complete from a successful cell run in an existing interactive
kernel.

Before an explicit push or PR update, inspect the full branch diff, run all
relevant repository and lesson checks, and repair failures in a bounded loop.
CI is the final branch-wide gate.

## Handoff

The handoff frontmatter is the latest resumable snapshot. Its body must state:

- completed work and changed files;
- decisions and definitions introduced;
- validation commands and results;
- unresolved questions or limitations.

Do not leave essential context only in the chat transcript.

At lesson end, checkpoint `review`, run the relevant full validation, and
explain the outputs to the learner. After the learner accepts completion,
checkpoint `completed`, update global navigation, push the lesson branch, open
one lesson PR, and observe CI. Squash merge only after explicit merge
confirmation.
