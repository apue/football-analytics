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
