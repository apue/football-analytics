# Academy conversion research contract

## Population and exit

The denominator contains every named player on each selected oldest-youth squad
roster. A player's exit season is their final observed roster season inside the
frozen roster window. Players whose final season falls outside the requested
exit interval are excluded from that cohort analysis.

Encode seasons by start year and treat requested endpoints as inclusive. The
frozen roster window must extend beyond the exit interval so continued academy
membership is observable rather than misclassified as exit.

## Observation and outcomes

Observe complete seasons after exit; the default window is five. For each
threshold, count eligible domestic senior-league appearances within each
competition tier. Do not add appearances across different tiers to cross a
threshold. Establishment requires one qualifying season; sustained establishment
requires the frozen number of qualifying seasons.

## Missingness

A below-threshold result is known only when every season in the observation
window has complete coverage. Partial or missing coverage produces `unknown`.
With incomplete adult-career data, confirmed positive outcomes and rates over
the full denominator are conservative lower bounds, not complete conversion
rates.

## Evidence ladder

- Source and row counts are data facts.
- Deterministic threshold outputs are metric results.
- Football meaning is interpretation.
- Academy quality, development effect, and causal explanations remain
  unverified hypotheses without an appropriate comparison design.
