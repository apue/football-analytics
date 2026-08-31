# Reuse index

- PR #8 `academy_conversion.py`: reuse deterministic cohort and outcome rules.
- PR #8 `academy_conversion_io.py`: reuse CSV validation and artifact writers.
- PR #8 `academy_study.py`: reduce to the frozen study fields still consumed.
- PR #8 roster/prototype/report modules: port only paths exercised by the
  Barcelona reproduction.
- PR #8 `web_acquisition.py`: reuse only safe request and error-handling
  concepts; do not port its routing or lifecycle.
- Existing repository `evidence.py`: match-level citation snapshots, not a web
  search extension point.
