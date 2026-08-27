# DECISIONS

Status: accepted

## Decision Log

### 2026-08-27: General academy-conversion pipeline from day one

Status: accepted

Core schemas and analysis are academy-neutral; Barcelona Juvenil A is the first
supported adapter and acceptance case.

### 2026-08-27: Deterministic engine, skill-operated workers

Status: accepted

Scripts own acquisition, parsing, validation, and calculation. The project
skill teaches agents how to operate the engine and handle exceptions.

### 2026-08-27: Provider-neutral acquisition envelope

Status: accepted

KeyPool/Firecrawl is the first provider, but downstream stages consume a stable
envelope so browser or licensed-dataset imports can replace it.

### 2026-08-27: Roster membership defines the denominator

Status: accepted

Include all reliably listed Juvenil A season-roster players, regardless of
youth appearances; assign each unique player to the final roster season.

### 2026-08-27: Five full post-exit seasons and appearance thresholds

Status: accepted

Observe five complete seasons after the final academy roster season. The main
threshold is 15 domestic senior-league appearances; 10 and 20 are sensitivity
thresholds. Two qualifying seasons means sustained.

### 2026-08-27: Hosting is a separate action

Status: accepted

Build and validate the visual report locally. Do not deploy without explicit
user confirmation.
