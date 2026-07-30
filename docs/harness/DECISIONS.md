# DECISIONS

Status: accepted

## D001: Public Main Repository

Decision: publish the learning code, curriculum, and football-related notes in a
public GitHub repository.

## D002: External Data Is Not Vendored

Decision: shallow-clone Hudl open data with blob filtering and sparse checkout
into an ignored directory, materialize lesson data on demand, and record its Git
commit when analyses are published.

## D003: Repository-Native Agent Memory

Decision: `AGENTS.md`, `course/state.yaml`, lesson artifacts, and Git history
are authoritative. Tool-specific Skills are optional accelerators.

## D004: Question-Led Curriculum

Decision: lessons progress from observable football questions to comparison,
inference, and modeling. Library APIs do not define the syllabus.

## D005: Local CPU First

Decision: all core lessons must run locally on CPU. GPU-only work is optional
and must declare its compute profile.

## D006: Progressive Curriculum Detail

Decision: define the full course map now, fully specify the opening stage, and
elaborate later stages near the point of use.

## D007: Pull Request CI

Decision: run the locked Python 3.12 environment, formatting, lint, tests,
course-state validation, and a clean-kernel notebook smoke test on pull
requests and pushes to `main`. Upstream match data remains outside CI.

## D008: Single Active Lesson With Local Checkpoints

Decision: schema v2 global state stores only navigation. The active lesson's
single handoff stores the latest resumable snapshot and short checkpoint
history. Meaningful learning units use `CP-NNN` local commits; lesson work is
not pushed until review is accepted.

## D009: Explicit Session Resume

Decision: every new agent session runs a read-only resume command, presents its
summary, and waits for learner confirmation. Dirty worktrees are treated as
post-checkpoint work to inspect, never as changes to discard or auto-commit.
